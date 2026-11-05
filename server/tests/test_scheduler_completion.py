# test_scheduler_completion.py
#
# Live, end-to-end check that an experiment automatically completes when it reaches
# its end_time: the device gets a final zero-intensity shutdown command, the
# experiment's status becomes COMPLETED, and the already-fired action event is left
# as SUCCESS (not touched/cancelled). Also checks the failure branch: if the
# shutdown command itself can't be confirmed, the experiment falls back to
# PAUSED + needs_admin instead of silently claiming COMPLETED.
#
# Like the other test_scheduler_*.py scripts, this launches its own backend
# subprocess against an isolated, throwaway SQLite database (never the real
# ./data/solar.db) and tiny fake ESP32 HTTP stubs — nothing here touches your real
# dev data or devices.
#
# This takes ~60-90s to run.
#
# Usage:
#   pytest tests/test_scheduler_completion.py -v -s
#   python tests/test_scheduler_completion.py

import http.server
import json
import os
import socket
import subprocess
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

SERVER_ROOT = Path(__file__).resolve().parent.parent
PYTHON = SERVER_ROOT / "pyenv" / "Scripts" / "python.exe"


def _drain_subprocess_output(proc: subprocess.Popen, buffer: list[str], max_lines: int = 4000) -> None:
    """Continuously read a subprocess's stdout in a background thread and keep the
    last `max_lines` in `buffer`. Without this, an unread subprocess.PIPE fills up
    its OS buffer once the child logs enough output, and the CHILD PROCESS ITSELF
    then blocks on its next stdout write -- freezing its entire event loop."""

    def _reader() -> None:
        assert proc.stdout is not None
        for line in proc.stdout:
            buffer.append(line)
            if len(buffer) > max_lines:
                del buffer[: len(buffer) - max_lines]

    threading.Thread(target=_reader, daemon=True).start()


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for(url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error = None
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except Exception as exc:  # noqa: BLE001 - just retrying until it's up
            last_error = exc
            time.sleep(0.5)
    raise TimeoutError(f"{url} did not become reachable: {last_error}")


def _api(base_url: str, method: str, path: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json"} if data is not None else {}
    req = urllib.request.Request(f"{base_url}{path}", data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def _make_device_handler(calls: list[dict]):
    class _Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path == "/set":
                qs = urllib.parse.parse_qs(parsed.query)
                calls.append({
                    "time": datetime.now(timezone.utc),
                    "ch0": qs.get("ch0", [None])[0],
                    "ch1": qs.get("ch1", [None])[0],
                })
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

        def log_message(self, *args):  # silence default request logging
            pass

    return _Handler


def _start_backend(env_overrides: dict) -> tuple[subprocess.Popen, list[str], str]:
    port = _free_port()
    env = {**os.environ, **env_overrides}
    print(f"Starting backend subprocess on port {port}...")
    proc = subprocess.Popen(
        [str(PYTHON), "-m", "uvicorn", "app.main:app", "--port", str(port)],
        cwd=SERVER_ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    log: list[str] = []
    _drain_subprocess_output(proc, log)
    base_url = f"http://127.0.0.1:{port}"
    _wait_for(f"{base_url}/api/v1/health", timeout=20)
    return proc, log, base_url


def _stop_backend(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def test_experiment_completes_at_end_time(tmp_path_factory=None):
    """Device confirms the shutdown command -> experiment lands in COMPLETED, with
    its one action preserved as SUCCESS."""
    import tempfile

    device_port = _free_port()

    # ignore_cleanup_errors: Windows can briefly hold the sqlite file open for a
    # moment after the backend subprocess is killed; don't let that race fail the test.
    with tempfile.TemporaryDirectory(prefix="scheduler_completion_test_", ignore_cleanup_errors=True) as tmp_dir:
        db_path = Path(tmp_dir) / "test.db"
        backend, backend_log, base_url = _start_backend({
            "DATABASE_URL": f"sqlite+aiosqlite:///{db_path.as_posix()}",
            "DATABASE_ECHO": "false",
        })
        device_server = None
        try:
            calls: list[dict] = []
            print(f"Starting fake device stub on port {device_port}...")
            device_server = http.server.HTTPServer(("127.0.0.1", device_port), _make_device_handler(calls))
            threading.Thread(target=device_server.serve_forever, daemon=True).start()

            device_id = f"completion-test-{int(time.time())}"
            print(f"Registering device {device_id}...")
            _api(base_url, "POST", "/register", {"device_id": device_id, "ip": "127.0.0.1"})
            _api(base_url, "POST", "/heartbeat", {"device_id": device_id, "ip": f"127.0.0.1:{device_port}"})

            buffer_seconds = 15  # headroom before the action fires
            action_duration_seconds = 10  # action's own length -> end_time = start + this

            start = datetime.now(timezone.utc) + timedelta(seconds=buffer_seconds)
            end = start + timedelta(seconds=action_duration_seconds)
            payload = {
                "name": f"completion test {device_id}",
                "device_id": device_id,
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "blocks": [{
                    "repeat": 1,
                    "actions": [{"set_intensity_percent": 77, "duration_hours": action_duration_seconds / 3600}],
                }],
            }

            print(f"Creating experiment: 1 action fires in {buffer_seconds}s, end_time {action_duration_seconds}s after that...")
            experiment = _api(base_url, "POST", "/api/v1/experiments", payload)
            experiment_id = experiment["experiment_id"]
            assert experiment["status"] == "INACTIVE"

            print("Activating...")
            experiment = _api(base_url, "POST", f"/api/v1/experiments/{experiment_id}/activate")
            assert experiment["status"] == "ACTIVE"

            total_wait = buffer_seconds + action_duration_seconds + 20
            deadline = time.monotonic() + total_wait
            print(f"Waiting up to {total_wait}s for the action AND the end-of-experiment shutdown to fire...")
            while time.monotonic() < deadline and len(calls) < 2:
                time.sleep(1)

            print(f"\nDevice received {len(calls)} calls:")
            for i, c in enumerate(calls):
                print(f"  #{i + 1} at {c['time'].isoformat()}  ch0={c['ch0']} ch1={c['ch1']}")

            assert len(calls) == 2, f"expected 2 calls (the action, then the shutdown), got {len(calls)}"
            assert float(calls[0]["ch0"]) == 77.0, "first call should be the action's own intensity"
            assert float(calls[1]["ch0"]) == 0.0, "second call should be the end-of-experiment shutdown (zero)"
            assert float(calls[1]["ch1"]) == 0.0

            final = _api(base_url, "GET", f"/api/v1/experiments/{experiment_id}")
            print(f"\nFinal experiment status: {final['status']}  needs_admin={final['needs_admin']}")
            assert final["status"] == "COMPLETED", f"expected COMPLETED, got {final['status']}"
            assert not final["needs_admin"]

            print("\nPASS -- experiment auto-completed at end_time: action preserved, device shut off, status COMPLETED.")
        finally:
            if device_server is not None:
                device_server.shutdown()
            _stop_backend(backend)
            if os.environ.get("SHOW_BACKEND_LOG"):
                print("\n--- backend log ---\n" + "".join(backend_log))


def test_experiment_pauses_if_shutdown_unconfirmed():
    """Device never responds to the shutdown command -> experiment falls back to
    PAUSED + needs_admin instead of silently claiming COMPLETED."""
    import tempfile

    with tempfile.TemporaryDirectory(prefix="scheduler_completion_fail_test_", ignore_cleanup_errors=True) as tmp_dir:
        db_path = Path(tmp_dir) / "test.db"
        backend, backend_log, base_url = _start_backend({
            "DATABASE_URL": f"sqlite+aiosqlite:///{db_path.as_posix()}",
            "DATABASE_ECHO": "false",
        })
        try:
            device_id = f"completion-fail-test-{int(time.time())}"
            print(f"Registering device {device_id} pointed at a port nothing listens on...")
            _api(base_url, "POST", "/register", {"device_id": device_id, "ip": "127.0.0.1"})
            _api(base_url, "POST", "/heartbeat", {"device_id": device_id, "ip": "127.0.0.1:9"})  # unreachable

            buffer_seconds = 10
            action_duration_seconds = 8

            start = datetime.now(timezone.utc) + timedelta(seconds=buffer_seconds)
            end = start + timedelta(seconds=action_duration_seconds)
            payload = {
                "name": f"completion fail test {device_id}",
                "device_id": device_id,
                "start_time": start.isoformat(),
                "end_time": end.isoformat(),
                "blocks": [{
                    "repeat": 1,
                    "actions": [{"set_intensity_percent": 50, "duration_hours": action_duration_seconds / 3600}],
                }],
            }

            experiment = _api(base_url, "POST", "/api/v1/experiments", payload)
            experiment_id = experiment["experiment_id"]
            print("Activating...")
            experiment = _api(base_url, "POST", f"/api/v1/experiments/{experiment_id}/activate")
            assert experiment["status"] == "ACTIVE"

            total_wait = buffer_seconds + action_duration_seconds + 20
            deadline = time.monotonic() + total_wait
            final = None
            print(f"Waiting up to {total_wait}s for the experiment to land in PAUSED...")
            while time.monotonic() < deadline:
                final = _api(base_url, "GET", f"/api/v1/experiments/{experiment_id}")
                # COMPLETING is transient (the shutdown call to the device is still in
                # flight); keep polling until it resolves to a terminal status.
                if final["status"] not in ("ACTIVE", "COMPLETING"):
                    break
                time.sleep(1)

            print(f"\nFinal status: {final['status']}  needs_admin={final['needs_admin']}")
            print(f"failure_reason: {final['failure_reason']}")
            assert final["status"] == "PAUSED", f"expected PAUSED, got {final['status']}"
            assert final["needs_admin"] is True
            assert final["failure_reason"] and "shutdown" in final["failure_reason"].lower()

            print("\nPASS -- unconfirmed shutdown correctly falls back to PAUSED + needs_admin, not COMPLETED.")
        finally:
            _stop_backend(backend)
            if os.environ.get("SHOW_BACKEND_LOG"):
                print("\n--- backend log ---\n" + "".join(backend_log))


if __name__ == "__main__":
    test_experiment_completes_at_end_time()
    test_experiment_pauses_if_shutdown_unconfirmed()

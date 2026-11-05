# test_scheduler_concurrent.py
#
# Live, end-to-end check that the scheduler correctly runs TWO experiments on TWO
# different (fake) ESP32 devices at the same time, without one interfering with or
# delaying the other. Both experiments share the same start time and action gaps, so
# their events are scheduled to fire at the exact same instant, pair by pair — the
# strictest version of "simultaneous" the scheduler could be asked to handle.
#
# Like test_scheduler_live.py, this launches its own backend subprocess against an
# isolated, throwaway SQLite database (never the real ./data/solar.db) and two tiny
# fake ESP32 HTTP stubs — nothing here touches your real dev data or devices.
#
# This takes ~2.5-3 minutes to run (6 actions, 20s apart, on each device).
#
# Usage:
#   pytest tests/test_scheduler_concurrent.py -v -s
#   python tests/test_scheduler_concurrent.py

import http.server
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
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
    then blocks on its next stdout write -- freezing its entire event loop (this is
    exactly what caused events to silently stop firing after the first batch when
    this test first captured the backend's log via stdout=PIPE without draining it)."""

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
    """Build a fresh BaseHTTPRequestHandler class that appends every /set call it
    receives to the given list. Each fake device needs its own handler/list pair."""

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


def test_two_experiments_run_concurrently():
    backend_port = _free_port()
    device_a_port = _free_port()
    device_b_port = _free_port()
    base_url = f"http://127.0.0.1:{backend_port}"

    # ignore_cleanup_errors: Windows can briefly hold the sqlite file open for a
    # moment after the backend subprocess is killed; don't let that race fail the test.
    with tempfile.TemporaryDirectory(prefix="scheduler_concurrent_test_", ignore_cleanup_errors=True) as tmp_dir:
        db_path = Path(tmp_dir) / "test.db"
        env = {
            **os.environ,
            "DATABASE_URL": f"sqlite+aiosqlite:///{db_path.as_posix()}",
            "DATABASE_ECHO": "false",
        }

        print(f"\nStarting backend subprocess on port {backend_port} (db={db_path})...")
        backend = subprocess.Popen(
            [str(PYTHON), "-m", "uvicorn", "app.main:app", "--port", str(backend_port)],
            cwd=SERVER_ROOT,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        backend_log: list[str] = []
        _drain_subprocess_output(backend, backend_log)
        device_a_server = None
        device_b_server = None
        try:
            _wait_for(f"{base_url}/api/v1/health", timeout=20)

            calls_a: list[dict] = []
            calls_b: list[dict] = []

            print(f"Starting fake device A stub on port {device_a_port}...")
            device_a_server = http.server.HTTPServer(("127.0.0.1", device_a_port), _make_device_handler(calls_a))
            threading.Thread(target=device_a_server.serve_forever, daemon=True).start()

            print(f"Starting fake device B stub on port {device_b_port}...")
            device_b_server = http.server.HTTPServer(("127.0.0.1", device_b_port), _make_device_handler(calls_b))
            threading.Thread(target=device_b_server.serve_forever, daemon=True).start()

            suffix = int(time.time())
            device_a_id = f"concurrent-test-a-{suffix}"
            device_b_id = f"concurrent-test-b-{suffix}"

            print(f"Registering device A ({device_a_id}) and device B ({device_b_id})...")
            _api(base_url, "POST", "/register", {"device_id": device_a_id, "ip": "127.0.0.1"})
            _api(base_url, "POST", "/heartbeat", {"device_id": device_a_id, "ip": f"127.0.0.1:{device_a_port}"})
            _api(base_url, "POST", "/register", {"device_id": device_b_id, "ip": "127.0.0.1"})
            _api(base_url, "POST", "/heartbeat", {"device_id": device_b_id, "ip": f"127.0.0.1:{device_b_port}"})

            intensities = [10.0, 30.0, 50.0, 70.0, 90.0, 100.0]
            gap_seconds = 20
            buffer_seconds = 20  # headroom before the first action, same as test_scheduler_live.py

            # Both experiments share the exact same start time and per-action gaps, so
            # every pair of corresponding events (A's Nth action, B's Nth action) is
            # scheduled to fire at the identical instant.
            start = datetime.now(timezone.utc) + timedelta(seconds=buffer_seconds)
            end = start + timedelta(seconds=gap_seconds * len(intensities) + 60)

            def build_payload(name: str, device_id: str) -> dict:
                return {
                    "name": name,
                    "device_id": device_id,
                    "start_time": start.isoformat(),
                    "end_time": end.isoformat(),
                    "blocks": [{
                        "repeat": 1,
                        "actions": [
                            {"set_intensity_percent": v, "duration_hours": gap_seconds / 3600}
                            for v in intensities
                        ],
                    }],
                }

            print(f"Creating two {len(intensities)}-action experiments, both starting in {buffer_seconds}s...")
            exp_a = _api(base_url, "POST", "/api/v1/experiments", build_payload(f"concurrent A {device_a_id}", device_a_id))
            exp_b = _api(base_url, "POST", "/api/v1/experiments", build_payload(f"concurrent B {device_b_id}", device_b_id))
            assert exp_a["status"] == "INACTIVE"
            assert exp_b["status"] == "INACTIVE"
            assert not calls_a and not calls_b, "nothing should fire before activation"

            print("Activating both experiments...")
            exp_a = _api(base_url, "POST", f"/api/v1/experiments/{exp_a['experiment_id']}/activate")
            exp_b = _api(base_url, "POST", f"/api/v1/experiments/{exp_b['experiment_id']}/activate")
            assert exp_a["status"] == "ACTIVE"
            assert exp_b["status"] == "ACTIVE"

            expected = len(intensities)
            total_wait = buffer_seconds + gap_seconds * expected + 20
            deadline = time.monotonic() + total_wait
            print(f"Waiting up to {total_wait}s for {expected} events on EACH device to fire...")
            while time.monotonic() < deadline and (len(calls_a) < expected or len(calls_b) < expected):
                time.sleep(1)

            print(f"\nDevice A received {len(calls_a)}/{expected} calls:")
            for i, c in enumerate(calls_a):
                print(f"  A#{i + 1} at {c['time'].isoformat()}  ch0={c['ch0']}")
            print(f"\nDevice B received {len(calls_b)}/{expected} calls:")
            for i, c in enumerate(calls_b):
                print(f"  B#{i + 1} at {c['time'].isoformat()}  ch0={c['ch0']}")

            assert len(calls_a) == expected, f"device A: expected {expected} commands, got {len(calls_a)}"
            assert len(calls_b) == expected, f"device B: expected {expected} commands, got {len(calls_b)}"

            # Each device must have received exactly its own experiment's values, in
            # order -- proves there's no cross-wiring between the two concurrent runs.
            for call, expected_value in zip(calls_a, intensities):
                assert float(call["ch0"]) == expected_value
                assert float(call["ch1"]) == expected_value
            for call, expected_value in zip(calls_b, intensities):
                assert float(call["ch0"]) == expected_value
                assert float(call["ch1"]) == expected_value

            # Corresponding A/B events were scheduled for the identical instant; a tight
            # gap between when each actually fired proves the scheduler ran both
            # concurrently instead of finishing one experiment before starting the other.
            print("\nDrift between A/B pairs scheduled for the same instant:")
            for i in range(expected):
                drift = abs((calls_a[i]["time"] - calls_b[i]["time"]).total_seconds())
                print(f"  pair #{i + 1}: {drift:.2f}s apart")
                assert drift <= 3, f"pair #{i + 1}: A and B fired {drift:.1f}s apart, expected near-simultaneous"

            print("\nPASS -- both experiments executed independently and simultaneously, with no cross-contamination.")
        finally:
            for server in (device_a_server, device_b_server):
                if server is not None:
                    server.shutdown()
            backend.terminate()
            try:
                backend.wait(timeout=10)
            except subprocess.TimeoutExpired:
                backend.kill()
            if os.environ.get("SHOW_BACKEND_LOG"):
                print("\n--- backend log ---\n" + "".join(backend_log))


if __name__ == "__main__":
    test_two_experiments_run_concurrently()

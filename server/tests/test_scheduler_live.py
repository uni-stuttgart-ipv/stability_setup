# test_scheduler_live.py
#
# Live, end-to-end check that the experiment scheduler actually fires commands at the
# right time: it launches its own backend subprocess against an isolated, throwaway
# SQLite database (never the real ./data/solar.db the frontend reads from), spins up
# a tiny fake ESP32 HTTP stub, creates and activates a short experiment through the
# real HTTP API, then watches the stub to confirm each action lands with the right
# intensity at the right time.
#
# This is deliberately NOT a mocked unit test — it exercises the real APScheduler
# instance, the real DB, and real wall-clock waits, so it takes ~30-60s to run.
#
# Usage:
#   pytest tests/test_scheduler_live.py -v -s
#   python tests/test_scheduler_live.py

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
    then blocks on its next stdout write -- freezing its entire event loop (confirmed
    as the root cause of a near-identical test silently stalling after a handful of
    events once the backend's INFO-level scheduler logging filled an undrained pipe)."""

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


class _FakeDeviceHandler(http.server.BaseHTTPRequestHandler):
    calls: list[dict] = []  # shared across requests; cleared per test run

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/set":
            qs = urllib.parse.parse_qs(parsed.query)
            _FakeDeviceHandler.calls.append({
                "time": datetime.now(timezone.utc),
                "ch0": qs.get("ch0", [None])[0],
                "ch1": qs.get("ch1", [None])[0],
            })
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

    def log_message(self, *args):  # silence default request logging
        pass


def test_scheduler_fires_events_in_order():
    _FakeDeviceHandler.calls = []
    backend_port = _free_port()
    device_port = _free_port()
    base_url = f"http://127.0.0.1:{backend_port}"

    # ignore_cleanup_errors: Windows can briefly hold the sqlite file open for a
    # moment after the backend subprocess is killed; don't let that race fail the test.
    with tempfile.TemporaryDirectory(prefix="scheduler_live_test_", ignore_cleanup_errors=True) as tmp_dir:
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
        device_server = None
        try:
            _wait_for(f"{base_url}/api/v1/health", timeout=20)

            print(f"Starting fake device stub on port {device_port}...")
            device_server = http.server.HTTPServer(("127.0.0.1", device_port), _FakeDeviceHandler)
            threading.Thread(target=device_server.serve_forever, daemon=True).start()

            device_id = f"scheduler-test-{int(time.time())}"
            intensities = [20.0, 60.0, 90.0]
            gap_seconds = 5
            buffer_seconds = 20  # headroom for request/process overhead before the first action fires

            print(f"Registering device {device_id}...")
            _api(base_url, "POST", "/register", {"device_id": device_id, "ip": "127.0.0.1"})
            _api(base_url, "POST", "/heartbeat", {"device_id": device_id, "ip": f"127.0.0.1:{device_port}"})

            start = datetime.now(timezone.utc) + timedelta(seconds=buffer_seconds)
            end = start + timedelta(hours=1)
            payload = {
                "name": f"scheduler live test {device_id}",
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

            print(f"Creating experiment with {len(intensities)} actions, first fires in {buffer_seconds}s...")
            experiment = _api(base_url, "POST", "/api/v1/experiments", payload)
            experiment_id = experiment["experiment_id"]
            assert experiment["status"] == "INACTIVE", "a freshly created experiment must start INACTIVE"
            assert not _FakeDeviceHandler.calls, "nothing should fire before activation"

            print("Activating...")
            experiment = _api(base_url, "POST", f"/api/v1/experiments/{experiment_id}/activate")
            assert experiment["status"] == "ACTIVE"

            expected = len(intensities)
            deadline = time.monotonic() + buffer_seconds + expected * gap_seconds + 15
            print(f"Waiting up to {deadline - time.monotonic():.0f}s for {expected} commands to fire...")
            while time.monotonic() < deadline and len(_FakeDeviceHandler.calls) < expected:
                time.sleep(1)

            calls = _FakeDeviceHandler.calls
            print(f"\nReceived {len(calls)}/{expected} calls:")
            for i, call in enumerate(calls):
                print(f"  #{i + 1} at {call['time'].isoformat()}  ch0={call['ch0']} ch1={call['ch1']}")

            assert len(calls) == expected, f"expected {expected} commands to fire, got {len(calls)}"

            for call, expected_intensity in zip(calls, intensities):
                assert float(call["ch0"]) == expected_intensity
                assert float(call["ch1"]) == expected_intensity

            gaps = [(calls[i + 1]["time"] - calls[i]["time"]).total_seconds() for i in range(len(calls) - 1)]
            for gap in gaps:
                assert abs(gap - gap_seconds) <= 2, f"expected ~{gap_seconds}s between commands, got {gap:.1f}s"

            final = _api(base_url, "GET", f"/api/v1/experiments/{experiment_id}")
            print(f"Final experiment status: {final['status']}")
            assert final["status"] == "ACTIVE"

            print("\nPASS -- all commands fired in order, on time, with the right values.")
        finally:
            if device_server is not None:
                device_server.shutdown()
            backend.terminate()
            try:
                backend.wait(timeout=10)
            except subprocess.TimeoutExpired:
                backend.kill()
            if os.environ.get("SHOW_BACKEND_LOG"):
                print("\n--- backend log ---\n" + "".join(backend_log))


if __name__ == "__main__":
    test_scheduler_fires_events_in_order()

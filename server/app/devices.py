# devices.py
#
# In-memory registry of connected ESP32 devices (device_id -> ip/last_seen/online),
# plus the one shared helper for actually sending an intensity command to a device.
# Lives in its own module so both main.py's HTTP routes and the scheduler can use it
# without main.py and scheduler.py importing each other.

from datetime import timedelta
from typing import Optional

import httpx

devices: dict[str, dict] = {}

# Threshold for considering a device offline if it hasn't sent a heartbeat recently.
OFFLINE_THRESHOLD = timedelta(seconds=120)


class DeviceNotRegisteredError(Exception):
    pass


async def send_intensity(device_id: str, ch0: Optional[int] = None, ch1: Optional[int] = None) -> str:
    """Send a channel-intensity command to a registered device. Returns the device's raw response text."""
    if device_id not in devices:
        raise DeviceNotRegisteredError(f"Device {device_id} not registered")

    ip = devices[device_id]["ip"]
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"http://{ip}/set",
            params={"ch0": ch0, "ch1": ch1},
            timeout=15,
        )
        return response.text

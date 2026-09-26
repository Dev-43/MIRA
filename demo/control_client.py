"""
FlytBase Control API Client
Provides typed access to /api/control/* endpoints for fault injection and drone control.
"""

import requests
from typing import Optional, List, Dict, Any
from dataclasses import dataclass


@dataclass
class HealthStatus:
    status: str
    simulator: str
    video: str
    uptime: int


@dataclass
class DeviceInfo:
    id: str
    type: str
    name: str
    dockId: Optional[str] = None
    droneId: Optional[str] = None


@dataclass
class SimState:
    running: bool
    speed: float
    tick: int
    drones: Dict[str, Any]


class ControlClient:
    """Client for FlytBase Control API at http://localhost:4000/api"""

    def __init__(self, base_url: str = "http://localhost:4000", timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.api_base = f"{self.base_url}/api"
        self.timeout = timeout
        self.session = requests.Session()

    def _get(self, path: str) -> Dict[str, Any]:
        resp = self.session.get(f"{self.api_base}{path}", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json_data: Dict[str, Any]) -> Dict[str, Any]:
        resp = self.session.post(f"{self.api_base}{path}", json=json_data, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _delete(self, path: str) -> Dict[str, Any]:
        resp = self.session.delete(f"{self.api_base}{path}", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    # Health & Devices
    def health_check(self) -> HealthStatus:
        """GET /api/health - System status"""
        data = self._get("/health")
        return HealthStatus(**data)

    def get_devices(self) -> List[DeviceInfo]:
        """GET /api/devices - List all drones and docks"""
        data = self._get("/devices")
        return [DeviceInfo(**d) for d in data.get("devices", [])]

    def get_sim_state(self) -> SimState:
        """GET /api/control/state - Full simulator snapshot"""
        data = self._get("/control/state")
        return SimState(**data)

    # Simulator Control
    def sim_control(self, action: str, speed: float = 1.0) -> Dict[str, Any]:
        """
        POST /api/control/sim
        action: "start" | "stop" | "reset"
        speed: simulation speed multiplier
        """
        if action not in ("start", "stop", "reset"):
            raise ValueError(f"Invalid action: {action}. Must be start, stop, or reset")
        return self._post("/control/sim", {"action": action, "speed": speed})

    # Drone Commands
    def command(self, device_id: str, action: str) -> Dict[str, Any]:
        """
        POST /api/control/command
        action: "takeoff" | "land"
        """
        if action not in ("takeoff", "land"):
            raise ValueError(f"Invalid action: {action}. Must be takeoff or land")
        return self._post("/control/command", {"deviceId": device_id, "type": action})

    def add_drone(self, name: str = "", latitude: float = 0.0, longitude: float = 0.0) -> Dict[str, Any]:
        """POST /api/control/drones - Add a new dock + drone pair"""
        return self._post("/control/drones", {"name": name, "latitude": latitude, "longitude": longitude})

    def remove_drone(self, device_id: str) -> Dict[str, Any]:
        """DELETE /api/control/drones/:id - Remove a drone and its dock"""
        return self._delete(f"/control/drones/{device_id}")

    # Video Control
    def video_control(self, action: str, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        POST /api/control/video
        action: "start" | "stop"
        device_id: optional, applies to all drones if omitted
        """
        if action not in ("start", "stop"):
            raise ValueError(f"Invalid action: {action}. Must be start or stop")
        payload = {"action": action}
        if device_id:
            payload["deviceId"] = device_id
        return self._post("/control/video", payload)

    # Fault Injection
    def inject_fault(
        self,
        kind: str,
        device_id: Optional[str] = None,
        seconds: Optional[int] = None,
        value: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        POST /api/control/fault - Inject a fault
        
        Fault kinds:
        - socket-kick: disconnect all clients once
        - socket-refuse: refuse handshakes (seconds, default 15)
        - socket-delay: delay telemetry by value ms ±50% (value default 1000)
        - socket-drop: drop value% of telemetry (value default 30)
        - sim-offline: kick + refuse simulator (seconds, default 15)
        - video-freeze: freeze video (seconds default 10, device_id optional)
        - video-stutter: 3 fps (device_id optional)
        - video-degrade: 320x180 @ 80kbps (device_id optional)
        - video-flicker: restart every value seconds (value default 5, device_id optional)
        """
        valid_kinds = {
            "socket-kick", "socket-refuse", "socket-delay", "socket-drop",
            "sim-offline", "video-freeze", "video-stutter", "video-degrade", "video-flicker"
        }
        if kind not in valid_kinds:
            raise ValueError(f"Invalid fault kind: {kind}. Valid: {valid_kinds}")

        payload = {"kind": kind}
        if device_id:
            payload["deviceId"] = device_id
        if seconds is not None:
            payload["seconds"] = seconds
        if value is not None:
            payload["value"] = value

        return self._post("/control/fault", payload)

    def list_faults(self) -> List[Dict[str, Any]]:
        """GET /api/control/fault - List active faults"""
        data = self._get("/control/fault")
        return data.get("faults", [])

    def clear_faults(self, kind: Optional[str] = None, device_id: Optional[str] = None) -> Dict[str, Any]:
        """
        DELETE /api/control/fault - Clear faults
        If kind specified, clear only that fault type
        If device_id specified with kind, clear only for that device
        """
        if kind:
            path = f"/control/fault/{kind}"
            if device_id:
                path += f"?deviceId={device_id}"
            return self._delete(path)
        return self._delete("/control/fault")


# Convenience functions for common fault scenarios
def inject_socket_kick(client: ControlClient) -> Dict[str, Any]:
    """Kick all connected cockpit clients"""
    return client.inject_fault("socket-kick")


def inject_socket_refuse(client: ControlClient, seconds: int = 15) -> Dict[str, Any]:
    """Refuse new socket connections"""
    return client.inject_fault("socket-refuse", seconds=seconds)


def inject_socket_delay(client: ControlClient, ms: int = 1000) -> Dict[str, Any]:
    """Delay telemetry by N ms ±50%"""
    return client.inject_fault("socket-delay", value=ms)


def inject_socket_drop(client: ControlClient, percent: int = 30) -> Dict[str, Any]:
    """Drop N% of telemetry messages"""
    return client.inject_fault("socket-drop", value=percent)


def inject_sim_offline(client: ControlClient, seconds: int = 15) -> Dict[str, Any]:
    """Kick and refuse simulator"""
    return client.inject_fault("sim-offline", seconds=seconds)


def inject_video_freeze(client: ControlClient, device_id: Optional[str] = None, seconds: int = 10) -> Dict[str, Any]:
    """Freeze video stream"""
    return client.inject_fault("video-freeze", device_id=device_id, seconds=seconds)


def inject_video_stutter(client: ControlClient, device_id: Optional[str] = None) -> Dict[str, Any]:
    """Reduce video to 3 fps"""
    return client.inject_fault("video-stutter", device_id=device_id)


def inject_video_degrade(client: ControlClient, device_id: Optional[str] = None) -> Dict[str, Any]:
    """Degrade video to 320x180 @ 80kbps"""
    return client.inject_fault("video-degrade", device_id=device_id)


def inject_video_flicker(client: ControlClient, device_id: Optional[str] = None, period: int = 5) -> Dict[str, Any]:
    """Restart video stream every N seconds"""
    return client.inject_fault("video-flicker", device_id=device_id, value=period)


def clear_all_faults(client: ControlClient) -> Dict[str, Any]:
    """Clear all active faults"""
    return client.clear_faults()


if __name__ == "__main__":
    # Quick test
    client = ControlClient()
    try:
        health = client.health_check()
        print(f"Health: {health.status}, Sim: {health.simulator}, Video: {health.video}")
        devices = client.get_devices()
        print(f"Devices: {[d.id for d in devices]}")
    except Exception as e:
        print(f"Error: {e}")
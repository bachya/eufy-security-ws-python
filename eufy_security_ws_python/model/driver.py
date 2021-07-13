"""Define the eufy-security-ws driver."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eufy_security_ws_python.event import Event, EventBase
from eufy_security_ws_python.model.device import Device
from eufy_security_ws_python.model.station import Station

if TYPE_CHECKING:
    from eufy_security_ws_python.client import WebsocketClient


class Driver(EventBase):
    """Define the driver."""

    def __init__(self, state: dict[str, Any]) -> None:
        """Initialize."""
        super().__init__()

        self._state = state
        self.devices: dict[str, Device] = {}
        self.stations: dict[str, Station] = {}

    @property
    def connected(self) -> bool:
        """Return whether the driver is connected."""
        return self._state["result"]["state"]["driver"]["connected"]

    @property
    def push_connected(self) -> bool:
        """Return whether the driver is connected to push events."""
        return self._state["result"]["state"]["driver"]["pushConnected"]

    @property
    def version(self) -> bool:
        """Return the version."""
        return self._state["result"]["state"]["driver"]["version"]

    @classmethod
    async def from_state(cls, client: "WebsocketClient", state: dict[str, Any]) -> None:
        """Save this station's metadata."""
        driver = cls(state)
        for device_state in state["result"]["state"]["devices"]:
            device = await Device.from_state(client, device_state)
            driver.devices[device.serial_number] = device
        for station_state in state["result"]["state"]["stations"]:
            station = await Station.from_state(client, station_state)
            driver.stations[station.serial_number] = station
        return driver

    def receive_event(self, event: Event) -> None:
        """React to an event."""
        if event.data["source"] == "station":
            station = self.stations[event.data["serialNumber"]]
            station.receive_event(event)
        elif event.data["source"] == "device":
            device = self.devices[event.data["serialNumber"]]
            device.receive_event(event)
        else:
            self._handle_event_protocol(event)

        self.emit(event.type, event.data)

"""Define the eufy-security-ws driver."""
from __future__ import annotations

from typing import TYPE_CHECKING

from eufy_security_ws_python.event import Event, EventBase
from eufy_security_ws_python.model.device import Device
from eufy_security_ws_python.model.station import Station

if TYPE_CHECKING:
    from eufy_security_ws_python.client import WebsocketClient


class Driver(EventBase):
    """Define the driver."""

    def __init__(self, client: "WebsocketClient", state: dict) -> None:
        """Initialize."""
        super().__init__()

        self._state = state
        self.stations: dict[str, Device] = {
            station_state["serialNumber"]: Station(client, station_state)
            for station_state in state["result"]["state"]["stations"]
        }
        self.devices: dict[str, Station] = {
            device_state["serialNumber"]: Device(client, device_state)
            for device_state in state["result"]["state"]["devices"]
        }

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

"""Define the eufy-security-ws driver."""
from typing import Dict

from ..event import Event, EventBase
from .device import Device
from .station import Station


class Driver(EventBase):
    """Define the driver."""

    def __init__(self, state: dict) -> None:
        """Initialize."""
        super().__init__()
        self._state = state
        self.connected = state["driver"]["connected"]
        self.push_connected = state["driver"]["pushConnected"]
        self.version = state["driver"]["version"]

        self.stations: Dict[str, Station] = {
            station["serialNumber"]: Station(station["serialNumber"], state)
            for station in state["stations"]
        }

        self.devices: Dict[str, Device] = {
            device["serialNumber"]: Device(device)
            for device in state["devices"]
        }

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

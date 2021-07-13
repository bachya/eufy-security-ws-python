"""Define a Eufy Security device."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from eufy_security_ws_python.event import Event, EventBase

if TYPE_CHECKING:
    from eufy_security_ws_python.client import WebsocketClient


class Device(EventBase):
    """Define a base device."""

    def __init__(self, client: "WebsocketClient", state: dict[str, Any]) -> None:
        """Initialize."""
        super().__init__()

        self._client = client
        self._state = state

    def __repr__(self) -> str:
        """Return the representation."""
        return f"<{type(self).__name__} name={self.name} serial={self.serial_number}>"

    def __hash__(self) -> int:
        """Return the hash."""
        return hash(self.serial_number)

    def __eq__(self, other: object) -> bool:
        """Return whether this instance equals another."""
        if not isinstance(other, Device):
            return False
        return self.serial_number == other.serial_number

    @property
    def enabled(self) -> bool:
        """Return whether the device is enabled."""
        return self._state["enabled"]

    @property
    def hardware_version(self) -> str:
        """Return the hardware version."""
        return self._state["hardwareVersion"]

    @property
    def model(self) -> str:
        """Return the model ID."""
        return self._state["model"]

    @property
    def name(self) -> str:
        """Return the name."""
        return self._state["name"]

    @property
    def serial_number(self) -> str:
        """Return the serial number."""
        return self._state["serialNumber"]

    @property
    def software_version(self) -> str:
        """Return the software version."""
        return self._state["softwareVersion"]

    @property
    def station_serial_number(self) -> str:
        """Return the serial number of the station."""
        return self._state["stationSerialNumber"]

    @property
    def type(self) -> str:
        """Return the type."""
        return self._state["type"]

    async def async_get_properties_metadata(self) -> dict[str, Any]:
        """Get all properties metadata for this device."""
        return await self._client.async_send_command(
            {
                "command": "device.get_properties_metadata",
                "serialNumber": self.serial_number,
            }
        )

    def handle_property_changed(self, event: Event) -> None:
        """Handle a "property changed" event."""
        self._state[event.data["name"]] = event.data["value"]

    def receive_event(self, event: Event) -> None:
        """React to an event."""
        self._handle_event_protocol(event)

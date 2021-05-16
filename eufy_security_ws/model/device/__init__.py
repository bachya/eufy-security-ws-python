"""Define a Eufy Security device."""
from ..event import Event, EventBase


class Device(EventBase):
    """Define a base device."""

    def __init__(self, device: dict) -> None:
        """Initialize."""
        super().__init__()
        self._device = device

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
        return self._device["enabled"]

    @property
    def hardware_version(self) -> str:
        """Return the hardware version."""
        return self._device["hardwareVersion"]

    @property
    def model(self) -> str:
        """Return the model ID."""
        return self._device["model"]

    @property
    def name(self) -> str:
        """Return the name."""
        return self._device["name"]

    @property
    def serial_number(self) -> str:
        """Return the serial number."""
        return self._device["serialNumber"]

    @property
    def software_version(self) -> str:
        """Return the software version."""
        return self._device["softwareVersion"]

    @property
    def station_serial_number(self) -> str:
        """Return the serial number of the station."""
        return self._device["stationSerialNumber"]

    def handle_property_changed(self, event: Event) -> None:
        """Handle a "property changed" event."""
        self._device[event.data["name"]] = event.data["value"]

    def receive_event(self, event: Event) -> None:
        """React to an event."""
        self._handle_event_protocol(event)

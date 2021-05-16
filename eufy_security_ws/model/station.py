"""Define a Eufy Security base station."""
from enum import Enum

from ..event import Event, EventBase


class AlarmMode(Enum):
    """Define a mapping of alarm modes to their integer counterparts."""

    AWAY = 0
    HOME = 1
    DISARMED = 63
    UNKNOWN = 99


class GuardMode(Enum):
    """Define a mapping of station modes to their integer counterparts."""

    AWAY = 0
    HOME = 1
    SCHEDULE = 2
    CUSTOM1 = 3
    CUSTOM2 = 4
    CUSTOM3 = 5
    GEO = 47
    DISARMED = 63
    UNKNOWN = 99


class Station(EventBase):
    """Define the station."""

    def __init__(self, serial_number: str, state: dict) -> None:
        """Initialize."""
        super().__init__()

        # Since this station's serial number is guaranteed to exist, it's safe to do
        # an auto-assigned list comprehension here:
        [self._station] = [
            station
            for station in state["stations"]
            if station["serialNumber"] == serial_number
        ]
        self._serial_number = serial_number

    def __repr__(self) -> str:
        """Return the representation."""
        return f"<{type(self).__name__} name={self.name} serial={self.serial_number}>"

    def __hash__(self) -> int:
        """Return the hash."""
        return hash(self.serial_number)

    def __eq__(self, other: object) -> bool:
        """Return whether this instance equals another."""
        if not isinstance(other, Station):
            return False
        return self.serial_number == other.serial_number

    @property
    def connected(self) -> bool:
        """Return whether the station is connected and online."""
        return self._station["connected"]

    @property
    def alarm_mode(self) -> AlarmMode:
        """Return the current alarm mode."""
        try:
            return AlarmMode(self._station["currentMode"])
        except ValueError:
            return AlarmMode.UNKNOWN

    @property
    def guard_mode(self) -> GuardMode:
        """Return the current guard mode."""
        try:
            return GuardMode(self._station["guardMode"])
        except ValueError:
            return GuardMode.UNKNOWN

    @property
    def hardware_version(self) -> str:
        """Return the hardware version."""
        return self._station["hardwareVersion"]

    @property
    def lan_ip_address(self) -> str:
        """Return the LAN IP address."""
        return self._station["lanIpAddress"]

    @property
    def mac_address(self) -> str:
        """Return the MAC address."""
        return self._station["macAddress"]

    @property
    def model(self) -> str:
        """Return the model ID."""
        return self._station["model"]

    @property
    def name(self) -> str:
        """Return the name."""
        return self._station["name"]

    @property
    def serial_number(self) -> str:
        """Return the serial number."""
        return self._serial_number

    @property
    def software_version(self) -> str:
        """Return the software version."""
        return self._station["softwareVersion"]

    def handle_connected(self, _: Event) -> None:
        """Handle a "connected" event."""

    def handle_disconnected(self, _: Event) -> None:
        """Handle a "disconnected" event."""

    def handle_guard_mode_changed(self, _: Event) -> None:
        """Handle a "guard mode changed" event."""

    def handle_property_changed(self, event: Event) -> None:
        """Handle a "property changed" event."""
        self._station[event.data["name"]] = event.data["value"]

    def receive_event(self, event: Event) -> None:
        """React to an event."""
        self._handle_event_protocol(event)

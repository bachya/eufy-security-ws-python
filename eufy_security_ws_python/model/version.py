"""Define utilities related to eufy-websocket-ws versions."""
from dataclasses import dataclass


@dataclass
class VersionInfo:
    """Define the server's version info."""

    driver_version: str
    server_version: str
    min_schema_version: int
    max_schema_version: int

    @classmethod
    def from_message(cls, msg: dict) -> "VersionInfo":
        """Create an instance from a version message."""
        return cls(
            driver_version=msg["driverVersion"],
            server_version=msg["serverVersion"],
            min_schema_version=msg.get("minSchemaVersion", 0),
            max_schema_version=msg.get("maxSchemaVersion", 0),
        )

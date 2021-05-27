"""Define package exceptions."""
from typing import Optional


class BaseEufySecurityServerError(Exception):
    """Define a base error."""

    pass


class TransportError(BaseEufySecurityServerError):
    """Define a transport-related exception."""


class CannotConnectError(TransportError):
    """Define a error when the websocket can't be connected to."""

    pass


class ConnectionClosed(TransportError):
    """Define a error when the websocket closes unexpectedly."""

    pass


class ConnectionFailed(TransportError):
    """Define a error when the websocket connection fails."""

    pass


class FailedCommand(BaseEufySecurityServerError):
    """Define a error related to a failed command."""

    def __init__(self, message_id: str, error_code: str, msg: Optional[str] = None):
        """Initialize a failed command error."""
        super().__init__(msg or f"Command failed: {error_code}")
        self.message_id = message_id
        self.error_code = error_code


class InvalidMessage(BaseEufySecurityServerError):
    """Define a error related to an invalid message from the websocket server."""

    pass


class InvalidServerVersion(BaseEufySecurityServerError):
    """Define a error related to an invalid eufy-websocket-ws schema version."""

    pass


class NotConnectedError(BaseEufySecurityServerError):
    """Define a error when the websocket hasn't been connected to."""

    pass

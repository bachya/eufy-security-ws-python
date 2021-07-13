"""Define a client to connect to the websocket server."""
from __future__ import annotations

import asyncio
from types import TracebackType
from typing import Any, Optional, cast
import uuid

from aiohttp import ClientSession, ClientWebSocketResponse, WSMsgType
from aiohttp.client_exceptions import (
    ClientError,
    ServerDisconnectedError,
    WSServerHandshakeError,
)

from eufy_security_ws_python.const import (
    LOGGER,
    MIN_SERVER_SCHEMA_VERSION,
    MAX_SERVER_SCHEMA_VERSION,
)
from eufy_security_ws_python.errors import (
    CannotConnectError,
    ConnectionClosed,
    ConnectionFailed,
    FailedCommand,
    InvalidMessage,
    InvalidServerVersion,
    NotConnectedError,
)
from eufy_security_ws_python.event import Event
from eufy_security_ws_python.model.driver import Driver
from eufy_security_ws_python.model.version import VersionInfo

SIZE_PARSE_JSON_EXECUTOR = 8192


class WebsocketClient:  # pylint: disable=too-many-instance-attributes
    """Define a websocket manager."""

    def __init__(self, ws_server_uri: str, session: ClientSession) -> None:
        """Initialize."""
        self._client: Optional[ClientWebSocketResponse] = None
        self._loop = asyncio.get_running_loop()
        self._result_futures: dict[str, asyncio.Future] = {}
        self._session = session
        self._shutdown_complete_event: Optional[asyncio.Event] = None
        self._ws_server_uri = ws_server_uri
        self.driver: Optional[Driver] = None
        self.schema_version = MAX_SERVER_SCHEMA_VERSION
        self.version: Optional[VersionInfo] = None

    async def __aenter__(self) -> "WebsocketClient":
        """Connect to the websocket."""
        await self.async_connect()
        return self

    async def __aexit__(
        self, exc_type: Exception, exc_value: str, traceback: TracebackType
    ) -> None:
        """Disconnect from the websocket."""
        await self.async_disconnect()

    @property
    def connected(self) -> bool:
        """Return if current connected to the websocket."""
        return self._client is not None and not self._client.closed

    def _parse_response_payload(self, payload: dict) -> None:
        """Handle a message from the websocket server."""
        if payload["type"] == "result":
            future = self._result_futures.get(payload["messageId"])

            if future is None:
                return

            if payload["success"]:
                future.set_result(payload["result"])
                return

            err = FailedCommand(payload["messageId"], payload["errorCode"])
            future.set_exception(err)
            return

        if payload["type"] != "event":
            LOGGER.debug(
                "Received message with unknown type '%s': %s",
                payload["type"],
                payload,
            )
            return

        event = Event(type=payload["event"]["event"], data=payload["event"])
        self.driver.receive_event(event)

    async def _async_receive_json(self) -> dict:
        """Receive a JSON response from the websocket server."""
        assert self._client
        msg = await self._client.receive()

        if msg.type in (WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.CLOSING):
            raise ConnectionClosed("Connection was closed.")

        if msg.type == WSMsgType.ERROR:
            raise ConnectionFailed()

        if msg.type != WSMsgType.TEXT:
            raise InvalidMessage(f"Received non-text message: {msg.type}")

        try:
            if len(msg.data) > SIZE_PARSE_JSON_EXECUTOR:
                data = await self._loop.run_in_executor(None, msg.json)
            else:
                data = msg.json()
        except ValueError as err:
            raise InvalidMessage("Received invalid JSON") from err

        LOGGER.debug("Received data from websocket server: %s", data)

        return data

    async def _async_send_json(self, payload: dict[str, Any]) -> None:
        """Send a JSON message to the websocket server.

        Raises NotConnectedError if client is not connected.
        """
        if not self.connected:
            raise NotConnectedError

        assert self._client
        assert "messageId" in payload

        LOGGER.debug("Sending data to websocket server: %s", payload)

        await self._client.send_json(payload)

    async def _async_set_api_schema(self) -> None:
        """Set the API schema version on server."""
        assert self._client

        await self._async_send_json(
            {
                "command": "set_api_schema",
                "messageId": "set_api_schema",
                "schemaVersion": self.schema_version,
            }
        )

        set_api_msg = await self._async_receive_json()

        if not set_api_msg["success"]:
            await self._client.close()
            raise FailedCommand(set_api_msg["messageId"], set_api_msg["errorCode"])

    async def async_connect(self) -> None:
        """Connect to the websocket server."""
        LOGGER.debug("Connecting to websocket server")

        try:
            self._client = await self._session.ws_connect(
                self._ws_server_uri, heartbeat=55
            )
        except ServerDisconnectedError as err:
            raise ConnectionClosed from err
        except (ClientError, WSServerHandshakeError) as err:
            raise CannotConnectError from err

        self.version = VersionInfo.from_message(await self._async_receive_json())

        if (
            self.version.min_schema_version > MIN_SERVER_SCHEMA_VERSION
            or self.version.max_schema_version < MAX_SERVER_SCHEMA_VERSION
        ):
            await self._client.close()
            raise InvalidServerVersion(
                f"eufy-websocket-js version is incompatible: {self.version.server_version}. "
                "Update eufy-websocket-ws to a version that supports a minimum API "
                f"schema of {MIN_SERVER_SCHEMA_VERSION}."
            )

        # Negotiate the highest available schema version and guard incompatibility with
        # the MIN_SERVER_SCHEMA_VERSION:
        if self.version.max_schema_version < MAX_SERVER_SCHEMA_VERSION:
            self.schema_version = self.version.max_schema_version

        LOGGER.info(
            "Connected to %s (Server %s, Driver %s, Using Schema %s)",
            self._ws_server_uri,
            self.version.server_version,
            self.version.driver_version,
            self.schema_version,
        )

    async def async_disconnect(self) -> None:
        """Disconnect from the websocket server."""
        if not self.connected:
            return

        LOGGER.debug("Disconnecting from websocket server")

        await self._client.close()

    async def async_listen(self, driver_ready: asyncio.Event) -> None:
        """Start listening to the websocket server.

        Raises NotConnectedError if client is not connected.
        """
        if not self.connected:
            raise NotConnectedError

        assert self._client

        try:
            await self._async_set_api_schema()
            await self._async_send_json(
                {"command": "start_listening", "messageId": "start_listening"}
            )

            state_msg = await self._async_receive_json()

            if not state_msg["success"]:
                await self._client.close()
                raise FailedCommand(state_msg["messageId"], state_msg["errorCode"])

            self.driver = cast(
                Driver,
                await self._loop.run_in_executor(
                    None,
                    Driver,
                    self,
                    state_msg,
                ),
            )
            driver_ready.set()

            LOGGER.info("Started listening to websocket server")

            while not self._client.closed:
                msg = await self._async_receive_json()
                self._parse_response_payload(msg)
        except ConnectionClosed:
            pass
        finally:
            LOGGER.debug("Listen completed; cleaning up")

            for future in self._result_futures.values():
                future.cancel()

            if not self._client.closed:
                await self._client.close()

            if self._shutdown_complete_event:
                self._shutdown_complete_event.set()

    async def async_send_command(
        self, payload: dict[str, Any], *, require_schema: int = None
    ) -> dict:
        """Send a command to the websocket server and wait for a response."""
        if require_schema and require_schema > self.schema_version:
            raise InvalidServerVersion(
                "Command unavailable due to an incompatible eufy-websocket-ws version. "
                "Update eufy-websocket-ws to a version that supports a minimum API "
                f"schema of {require_schema}."
            )

        future: "asyncio.Future[dict]" = self._loop.create_future()
        message_id = payload["messageId"] = uuid.uuid4().hex
        self._result_futures[message_id] = future
        await self._async_send_json(payload)
        try:
            return await future
        finally:
            self._result_futures.pop(message_id)

    async def async_send_command_no_wait(
        self, payload: dict[str, Any], *, require_schema: int = None
    ) -> dict:
        """Send a command to the websocket server and don't wait for a response."""
        if require_schema and require_schema > self.schema_version:
            raise InvalidServerVersion(
                "Command unavailable due to an incompatible eufy-websocket-ws version. "
                "Update eufy-websocket-ws to a version that supports a minimum API "
                f"schema of {require_schema}."
            )

        payload["messageId"] = uuid.uuid4().hex
        await self._async_send_json(payload)

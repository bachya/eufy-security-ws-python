"""Define tests for the client."""
import asyncio
from unittest.mock import Mock

from aiohttp.client_exceptions import ClientError, WSServerHandshakeError
from aiohttp.client_reqrep import ClientResponse, RequestInfo
from aiohttp.http_websocket import WSMsgType
import pytest

from eufy_security_ws_python.client import WebsocketClient
from eufy_security_ws_python.const import MAX_SERVER_SCHEMA_VERSION
from eufy_security_ws_python.errors import (
    CannotConnectError,
    ConnectionFailed,
    FailedCommand,
    InvalidMessage,
    InvalidServerVersion,
    NotConnectedError,
)

pytestmark = pytest.mark.asyncio

# pylint: disable=too-many-arguments


@pytest.mark.parametrize(
    "error",
    [ClientError, WSServerHandshakeError(Mock(RequestInfo), (Mock(ClientResponse),))],
)
async def test_cannot_connect(client_session, error, url):
    """Test cannot connect."""
    client_session.ws_connect.side_effect = error
    client = WebsocketClient(url, client_session)

    with pytest.raises(CannotConnectError):
        await client.async_connect()

    assert not client.connected


async def test_command_error_handling(client, mock_command):
    """Test error handling."""
    mock_command(
        {"command": "some_command"}, {"errorCode": "unknown_command",}, False,
    )

    with pytest.raises(FailedCommand) as raised:
        await client.async_send_command({"command": "some_command"})

    assert raised.value.error_code == "unknown_command"


async def test_connect_disconnect(client_session, url):
    """Test client connect and disconnect."""
    async with WebsocketClient(url, client_session) as client:
        assert client.connected

    assert not client.connected


async def test_listen(client_session, driver_ready, url):
    """Test client listen."""
    client = WebsocketClient(url, client_session)

    assert not client.driver

    await client.async_connect()

    assert client.connected

    asyncio.create_task(client.async_listen(driver_ready))
    await driver_ready.wait()
    assert client.driver

    await client.async_disconnect()
    assert not client.connected


async def test_listen_client_error(
    client_session, driver_ready, messages, url, ws_client, ws_message
):
    """Test websocket error on listen."""
    client = WebsocketClient(url, client_session)
    await client.async_connect()
    assert client.connected

    messages.append(ws_message)

    ws_client.receive.side_effect = asyncio.CancelledError()

    # This should break out of the listen loop before any message is received:
    with pytest.raises(asyncio.CancelledError):
        await client.async_listen(driver_ready)

    assert not ws_message.json.called


@pytest.mark.parametrize(
    "message_type", [WSMsgType.CLOSE, WSMsgType.CLOSED, WSMsgType.CLOSING]
)
async def test_listen_disconnect_message_types(
    client_session, driver_ready, message_type, messages, url, ws_client, ws_message
):
    """Test different websocket message types that stop listen."""
    async with WebsocketClient(url, client_session) as client:
        assert client.connected
        ws_message.type = message_type
        messages.append(ws_message)

        # This should break out of the listen loop before handling the received message;
        # otherwise there will be an error:
        await client.async_listen(driver_ready)

    # Assert that we received a message:
    ws_client.receive.assert_awaited()


@pytest.mark.parametrize(
    "message_type, exception",
    [(WSMsgType.ERROR, ConnectionFailed), (WSMsgType.BINARY, InvalidMessage),],
)
async def test_listen_error_message_types(
    client_session, driver_ready, exception, message_type, messages, url, ws_message
):
    """Test different websocket message types that should raise on listen."""
    client = WebsocketClient(url, client_session)
    await client.async_connect()
    assert client.connected

    ws_message.type = message_type
    messages.append(ws_message)

    with pytest.raises(exception):
        await client.async_listen(driver_ready)


async def test_listen_event(
    client_session, url, ws_client, messages, ws_message, result, driver_ready
):
    """Test receiving event result type on listen."""
    client = WebsocketClient(url, client_session)
    await client.async_connect()

    assert client.connected

    result["type"] = "event"
    result["event"] = {
        "source": "station",
        "event": "property changed",
        "serialNumber": "ABCDEF1234567890",
        "name": "currentMode",
        "value": 63,
        "timestamp": 1622949673501,
    }
    messages.append(ws_message)

    await client.async_listen(driver_ready)
    ws_client.receive.assert_awaited()


async def test_listen_invalid_message_data(
    client_session, driver_ready, messages, url, ws_message
):
    """Test websocket message data that should raise on listen."""
    client = WebsocketClient(url, client_session)
    await client.async_connect()
    assert client.connected

    ws_message.json.side_effect = ValueError("Boom")
    messages.append(ws_message)

    with pytest.raises(InvalidMessage):
        await client.async_listen(driver_ready)


async def test_listen_not_success(client_session, driver_ready, result, url):
    """Test receive result message with success False on listen."""
    result["success"] = False
    result["errorCode"] = "error_code"

    client = WebsocketClient(url, client_session)
    await client.async_connect()

    with pytest.raises(FailedCommand):
        await client.async_listen(driver_ready)

    assert not client.connected


async def test_listen_unknown_result_type(
    client_session, url, ws_client, result, driver_ready, driver
):
    """Test websocket message with unknown type on listen."""
    client = WebsocketClient(url, client_session)
    await client.async_connect()

    assert client.connected

    # Make sure there's a driver so we can test an unknown event.
    client.driver = driver
    result["type"] = "unknown"

    # Receiving an unknown message type should not error.
    await client.async_listen(driver_ready)

    ws_client.receive.assert_awaited()


async def test_listen_without_connect(client_session, driver_ready, url):
    """Test listen without first being connected."""
    client = WebsocketClient(url, client_session)
    assert not client.connected

    with pytest.raises(NotConnectedError):
        await client.async_listen(driver_ready)


async def test_max_schema_version(client_session, url, version_data):
    """Test client connect with an invalid schema version."""
    version_data["maxSchemaVersion"] = 0
    client = WebsocketClient(url, client_session)

    with pytest.raises(InvalidServerVersion):
        await client.async_connect()

    assert not client.connected


async def test_min_schema_version(client_session, url, version_data):
    """Test client connect with invalid schema version."""
    version_data["minSchemaVersion"] = 100
    client = WebsocketClient(url, client_session)

    with pytest.raises(InvalidServerVersion):
        await client.async_connect()

    assert not client.connected


async def test_send_json_when_disconnected(client_session, url):
    """Test sending a JSON message when disconnected."""
    client = WebsocketClient(url, client_session)

    assert not client.connected

    with pytest.raises(NotConnectedError):
        await client.async_send_command({"test": None})


async def test_send_unsupported_command(
    client_session, driver, driver_ready, url, ws_client
):
    """Test sending unsupported command."""
    client = WebsocketClient(url, client_session)
    await client.async_connect()
    assert client.connected
    client.driver = driver
    await client.async_listen(driver_ready)
    ws_client.receive.assert_awaited()

    # Test schema version is at server maximum:
    if client.version.max_schema_version < MAX_SERVER_SCHEMA_VERSION:
        assert client.schema_version == client.version.max_schema_version

    # Ensure a command with the current schema version doesn't fail:
    with pytest.raises(NotConnectedError):
        await client.async_send_command(
            {"command": "test"}, require_schema=client.schema_version
        )
    # send command of unsupported schema version should fail
    with pytest.raises(InvalidServerVersion):
        await client.async_send_command(
            {"command": "test"}, require_schema=client.schema_version + 2
        )
    with pytest.raises(InvalidServerVersion):
        await client.async_send_command_no_wait(
            {"command": "test"}, require_schema=client.schema_version + 2
        )


async def test_set_api_schema_not_success(
    client_session, driver_ready, set_api_schema_data, url
):
    """Test receive result message with success False on listen."""
    set_api_schema_data["success"] = False
    set_api_schema_data["errorCode"] = "error_code"

    client = WebsocketClient(url, client_session)
    await client.async_connect()

    with pytest.raises(FailedCommand):
        await client.async_listen(driver_ready)

    assert not client.connected

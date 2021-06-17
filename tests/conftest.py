"""Define dynamic test fixtures."""
import asyncio
from collections import deque
import json
from typing import List, Tuple
from unittest.mock import AsyncMock, Mock, patch

from aiohttp import ClientSession, ClientWebSocketResponse
from aiohttp.http_websocket import WSMessage, WSMsgType
import pytest

from eufy_security_ws_python.client import WebsocketClient
from eufy_security_ws_python.model.driver import Driver

from .common import load_fixture

TEST_URL = "ws://test.org:3000"

# pylint: disable=protected-access, unused-argument


def create_ws_message(result):
    """Return a mock WSMessage."""
    message = Mock(spec_set=WSMessage)
    message.type = WSMsgType.TEXT
    message.data = json.dumps(result)
    message.json.return_value = result
    return message


@pytest.fixture(name="client")
async def client_fixture(client_session, loop, url, ws_client):
    """Return a client with a mock websocket transport.

    This fixture needs to be a coroutine function to get an event loop
    when creating the client.
    """
    client = WebsocketClient(url, client_session)
    client._client = ws_client
    return client


@pytest.fixture(name="client_session")
def client_session_fixture(ws_client):
    """Mock an aiohttp client session."""
    client_session = AsyncMock(spec_set=ClientSession)
    client_session.ws_connect.side_effect = AsyncMock(return_value=ws_client)
    return client_session


@pytest.fixture(name="controller_state", scope="session")
def controller_state_fixture():
    """Load the controller state fixture data."""
    return json.loads(load_fixture("controller_state.json"))


@pytest.fixture(name="driver")
def driver_fixture(client, result):
    """Return a driver instance with a supporting client."""
    return Driver(client, result)


@pytest.fixture(name="driver_ready")
async def driver_ready_fixture(loop):
    """Return an asyncio.Event for driver ready."""
    return asyncio.Event()


@pytest.fixture(name="messages")
def messages_fixture():
    """Return a message buffer for the WS client."""
    return deque()


@pytest.fixture(name="mock_command")
def mock_command_fixture(ws_client, client, uuid4):
    """Mock a command and response."""
    mock_responses: List[Tuple[dict, dict, bool]] = []
    ack_commands: List[dict] = []

    def apply_mock_command(
        match_command: dict, response: dict, success: bool = True
    ) -> List[dict]:
        """Apply the mock command and response return value to the transport.

        Return the list with correctly acknowledged commands.
        """
        mock_responses.append((match_command, response, success))
        return ack_commands

    async def set_response(message):
        """Check the message and set the mocked response if a command matches."""
        for match_command, response, success in mock_responses:
            if all(message[key] == value for key, value in match_command.items()):
                ack_commands.append(message)
                received_message = {
                    "type": "result",
                    "messageId": uuid4,
                    "success": success,
                }
                if success:
                    received_message["result"] = response
                else:
                    received_message.update(response)
                client._parse_response_payload(received_message)
                return

        raise RuntimeError("Command not mocked!")

    ws_client.send_json.side_effect = set_response

    return apply_mock_command


@pytest.fixture(name="uuid4")
def mock_uuid4_fixture():
    """Return a mocked websocket UUID-based message ID."""
    uuid4_hex = "1234"
    with patch("uuid.uuid4") as uuid4:
        uuid4.return_value.hex = uuid4_hex
        yield uuid4_hex


@pytest.fixture(name="result")
def result_fixture(controller_state, uuid4):
    """Return a server result message."""
    return {
        "messageId": uuid4,
        "result": {"state": controller_state},
        "success": True,
        "type": "result",
    }


@pytest.fixture(name="set_api_schema_data")
def set_api_schema_data_fixture():
    """Return a payload with API schema data."""
    return {
        "messageId": "set_api_schema",
        "result": {},
        "success": True,
        "type": "result",
    }


@pytest.fixture(name="url")
def url_fixture():
    """Return a test url."""
    return TEST_URL


@pytest.fixture(name="version_data")
def version_data_fixture(loop):
    """Return a payload with version data."""
    return {
        "driverVersion": "0.8.2",
        "maxSchemaVersion": 1,
        "minSchemaVersion": 0,
        "serverVersion": "0.1.2",
        "type": "version",
    }


@pytest.fixture(name="ws_client")
async def ws_client_fixture(
    loop, messages, result, set_api_schema_data, version_data,
):
    """Mock a websocket client.

    This fixture only allows a single message to be received.
    """
    ws_client = AsyncMock(spec_set=ClientWebSocketResponse, closed=False)
    ws_client.receive_json.side_effect = (version_data, set_api_schema_data, result)
    for data in (version_data, set_api_schema_data, result):
        messages.append(create_ws_message(data))

    async def receive():
        """Return a websocket message."""
        await asyncio.sleep(0)

        message = messages.popleft()
        if not messages:
            ws_client.closed = True

        return message

    ws_client.receive.side_effect = receive

    async def close_client(msg):
        """Close the client."""
        if msg["command"] in ("set_api_schema", "start_listening"):
            return

        await asyncio.sleep(0)
        ws_client.closed = True

    ws_client.send_json.side_effect = close_client

    async def reset_close():
        """Reset the websocket client close method."""
        ws_client.closed = True

    ws_client.close.side_effect = reset_close

    return ws_client


@pytest.fixture(name="ws_message")
def ws_message_fixture(result):
    """Return a mock WSMessage."""
    return create_ws_message(result)

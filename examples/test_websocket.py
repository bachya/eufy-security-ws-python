"""Define a websocket test."""
import asyncio
import logging

from aiohttp import ClientSession

from eufy_security_ws_python.client import WebsocketClient
from eufy_security_ws_python.errors import CannotConnectError

_LOGGER = logging.getLogger()


async def main() -> None:
    """Run the websocket example."""
    logging.basicConfig(level=logging.DEBUG)

    async with ClientSession() as session:
        client = WebsocketClient("ws://localhost:3000", session)

        try:
            await client.async_connect()
        except CannotConnectError as err:
            _LOGGER.error("There was a error while connecting to the server: %s", err)
            return

        driver_ready = asyncio.Event()
        await client.async_listen(driver_ready)


asyncio.run(main())

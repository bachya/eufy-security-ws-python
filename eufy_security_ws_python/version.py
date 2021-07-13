"""Define a version helper."""
import aiohttp

from eufy_security_ws_python.model.version import VersionInfo


async def async_get_server_version(
    url: str, session: aiohttp.ClientSession
) -> VersionInfo:
    """Return a server version."""
    client = await session.ws_connect(url)
    try:
        return VersionInfo.from_message(await client.receive_json())
    finally:
        await client.close()

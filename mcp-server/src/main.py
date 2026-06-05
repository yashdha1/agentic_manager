import asyncio
import sys
from contextlib import asynccontextmanager

from core.db.pg_engine import ensure_schema_presence
from core.db.qdrant_client import QdrantClientManager
from core.logger import logger
from fastmcp import FastMCP
from tools import mcp as tools_mcp


def _suppress_windows_connection_reset() -> None:
    """Windows Proactor loop raises ConnectionResetError when HTTP clients
    close connections. Suppress this cosmetic noise."""
    if sys.platform != "win32":
        return

    loop = asyncio.get_event_loop()

    def _handler(loop, context):
        exc = context.get("exception")
        if isinstance(exc, ConnectionResetError):
            return
        loop.default_exception_handler(context)

    loop.set_exception_handler(_handler)


@asynccontextmanager
async def lifespan(server: FastMCP):
    _suppress_windows_connection_reset()
    await ensure_schema_presence()
    QdrantClientManager.create_collections()
    yield
    logger.info("Shutting DOWN MCP Server")


mcp = FastMCP(
    "ecomm_mcp",
    lifespan=lifespan,
)

mcp.mount(tools_mcp)


@mcp.tool
def greet(name: str) -> str:
    """Greet a user by name."""
    return f"Hello, {name}!"

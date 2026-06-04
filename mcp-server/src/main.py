from contextlib import asynccontextmanager

from core.db.pg_engine import ensure_schema_presence
from core.db.qdrant_client import QdrantClientManager
from core.logger import logger
from fastmcp import FastMCP
from tools import mcp as tools_mcp


@asynccontextmanager
async def lifespan(server: FastMCP):
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

from contextlib import asynccontextmanager

from core.db.pg_engine import ensure_schema_presence
from core.db.qdrant_client import QdrantClientManager
from core.logger import logger
from fastmcp import FastMCP


@asynccontextmanager
async def lifespan(server: FastMCP):
    await ensure_schema_presence()
    QdrantClientManager.create_collections()
    yield
    logger.info("Shutting DOWN MCP Server")


mcp = FastMCP(
    "e_commerce_mcp",
    lifespan=lifespan,
)


@mcp.tool
def greet(name: str) -> str:
    """Greet a user by name."""
    return f"Hello, {name}!"

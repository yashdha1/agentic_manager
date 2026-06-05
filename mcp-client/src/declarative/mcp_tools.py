import asyncio

import httpx
from langchain_mcp_adapters.client import MultiServerMCPClient

from src.core.config import settings
from src.core.logger import logger

_RETRY_ATTEMPTS = 10
_RETRY_DELAY = 2.0  # seconds


async def _wait_for_mcp_server() -> None:
    """Poll the MCP server until it responds or retries are exhausted."""
    url = f"{settings.mcp_server_url}/mcp"
    async with httpx.AsyncClient() as http:
        for attempt in range(1, _RETRY_ATTEMPTS + 1):
            try:
                await http.get(url, timeout=2.0)
                return  # any response (even 405) means server is up
            except (httpx.ConnectError, httpx.TimeoutException):
                logger.warning(f"MCP server not ready (attempt {attempt}/{_RETRY_ATTEMPTS})," 
                               f" retrying in {_RETRY_DELAY}s...")
                await asyncio.sleep(_RETRY_DELAY)
    raise RuntimeError(f"MCP server at {url} did not become ready after"
                       f"{_RETRY_ATTEMPTS} attempts.")


def get_mcp_client() -> MultiServerMCPClient:
    """Factory function to create an MCP client instance."""
    return MultiServerMCPClient(
        {
            "ecomm": {
                "url": f"{settings.mcp_server_url}/mcp",
                "transport": "streamable_http",
            }
        }
    )


async def prepare_workflow() -> None:
    """Wait for MCP server, fetch tools, store them, and initialise agents."""
    from src.declarative.AgentSpec import store_tools
    from src.declarative.agent_static import init_agents
    from src.declarative.workflow import init_workflow

    await _wait_for_mcp_server()
    client = get_mcp_client()
    tools = await client.get_tools()
    logger.info(f"Loaded {len(tools)} tools from MCP server")
    store_tools(tools)
    init_agents()
    init_workflow()
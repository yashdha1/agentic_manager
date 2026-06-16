import asyncio
import json
from typing import Any

import httpx
from langchain_core.tools import BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient

from src.core.config import settings
from src.core.logger import logger


def _ensure_str(value: Any) -> str:
    """Return value as a string; JSON-serialize dicts/lists."""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, default=str)
    except Exception:
        return str(value)


def _coerce(result: Any, content_and_artifact: bool) -> Any:
    """Coerce a tool result so its string content satisfies the LLM API."""
    if content_and_artifact:
        # LangChain expects (str_content, artifact); only stringify the first element.
        if isinstance(result, (list, tuple)) and len(result) == 2:
            return (_ensure_str(result[0]), result[1])
        return (_ensure_str(result), result)
    return _ensure_str(result)


def _wrap_tool(tool: BaseTool) -> BaseTool:
    """Ensure tool always returns str-compatible content on both sync and async paths."""
    caa = getattr(tool, "response_format", None) == "content_and_artifact"

    original_run = tool._run

    def _run(*args: Any, **kwargs: Any) -> Any:
        return _coerce(original_run(*args, **kwargs), caa)

    tool._run = _run  # type: ignore[method-assign]

    # StructuredTool calls self.coroutine directly in _arun; wrap it here.
    if getattr(tool, "coroutine", None) is not None:
        original_coroutine = tool.coroutine  # type: ignore[attr-defined]

        async def _coroutine(*args: Any, **kwargs: Any) -> Any:
            return _coerce(await original_coroutine(*args, **kwargs), caa)

        tool.coroutine = _coroutine  # type: ignore[attr-defined]

    return tool

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


async def prepare_workflow(checkpointer) -> None:
    """Wait for MCP server, fetch tools, store them, and initialise agents."""
    from src.declarative.agent_static import init_agents
    from src.declarative.AgentSpec import store_tools
    from src.declarative.workflow import init_workflow

    await _wait_for_mcp_server()
    client = get_mcp_client()
    raw_tools = await client.get_tools()
    tools = [_wrap_tool(t) for t in raw_tools]
    logger.info(f"Loaded {len(tools)} tools from MCP server")
    store_tools(tools)
    init_agents()
    init_workflow(checkpointer)
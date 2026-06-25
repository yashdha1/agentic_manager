import enum

from langchain_core.tools import BaseTool


class AgentsTool(enum.Enum):
    """Maps each agent to its MCP tool-name prefix."""
    ORCHESTRATOR = "orchestrator_"
    SALES        = "sales_"
    CUSTOMER     = "customers_"
    KNOWLEDGE    = "knowledge_"
    INVENTORY    = "inventory_"

class Agent(enum.Enum):
    ORCHESTRATOR = "orchestrator"
    SALES        = "sales"
    CUSTOMER     = "customers"
    KNOWLEDGE    = "knowledge"
    INVENTORY    = "inventory"

# Module-level tool store — populated once at FastAPI startup via store_tools().
_all_tools: list[BaseTool] = []


def store_tools(tools: list[BaseTool]) -> None:
    """Called at startup after fetching tools from the MCP server."""
    _all_tools.clear()
    _all_tools.extend(tools)


def get_tools_for(agent: AgentsTool) -> list[BaseTool]:
    """Return only the tools whose name starts with the agent's prefix."""
    return [t for t in _all_tools if t.name.startswith(agent.value)]
 
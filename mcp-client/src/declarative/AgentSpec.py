import enum

from langchain_core.tools import BaseTool
from pydantic import BaseModel, model_validator


class AgentsTool(enum.Enum):
    """Maps each agent to its MCP tool-name prefix."""
    ORCHESTRATOR = "orchestrator_"
    SALES        = "sales_"
    CUSTOMER     = "customers_"
    KNOWLEDGE    = "knowledge_"
    INVENTORY    = "inventory_"

class Agent(enum.Enum):
    ORCHESTRATOR = "orchestrator agent"
    SALES        = "sales agent"
    CUSTOMER     = "customer support agent"
    KNOWLEDGE    = "knowledge agent"
    INVENTORY    = "inventory manager agent"

# Module-level tool store — populated once at FastAPI startup via store_tools().
_all_tools: list[BaseTool] = []


def store_tools(tools: list[BaseTool]) -> None:
    """Called at startup after fetching tools from the MCP server."""
    _all_tools.clear()
    _all_tools.extend(tools)


def get_tools_for(agent: AgentsTool) -> list[BaseTool]:
    """Return only the tools whose name starts with the agent's prefix."""
    return [t for t in _all_tools if t.name.startswith(agent.value)]

class AgentSpec(BaseModel):
    """Declarative agent specification with auto-filtered MCP tools."""

    name: Agent
    system_prompt: str = ""
    user_prompt: str = ""

    tools: list[BaseTool] = []

    model_config = {"arbitrary_types_allowed": True}

    @model_validator(mode="after")
    def _populate_tools(self) -> "AgentSpec":
        if not self.tools:
            self.tools = get_tools_for(self.name)
        return self

    ... 
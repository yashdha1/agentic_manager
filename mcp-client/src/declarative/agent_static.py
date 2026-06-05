from pathlib import Path

from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import create_react_agent

from src.core.config import settings
from src.declarative.AgentSpec import AgentsTool, get_tools_for
from src.models.AgentOutput import OrchestratorOutput

_AGENTS_DIR = Path(__file__).parent / "agents"


def _load_md(filename: str) -> str:
    return (_AGENTS_DIR / filename).read_text(encoding="utf-8")


# Module-level agent instances — None until init_agents() is called at startup.
orchestrator = None
sales_agent = None
customer_agent = None
inventory_agent = None
knowledge_agent = None
_model = None  # shared model instance exposed for other modules (e.g. workflow.py)


def init_agents() -> None:
    """Create all agent instances using tools already stored via store_tools()."""
    global orchestrator, sales_agent, customer_agent, inventory_agent, knowledge_agent, _model

    _model = AzureChatOpenAI(
        azure_deployment=settings.azure_chat_model,
        api_version=settings.azure_api_version,
        azure_endpoint=settings.azure_endpoint,
        api_key=settings.azure_api_key.get_secret_value() if settings.azure_api_key else None,
    )

    orchestrator = create_react_agent(
        _model,
        tools=get_tools_for(AgentsTool.ORCHESTRATOR),
        prompt=_load_md("orchestrator.md"),
        response_format=OrchestratorOutput,
    )

    sales_agent = create_react_agent(
        _model,
        tools=get_tools_for(AgentsTool.SALES),
        prompt=_load_md("sales.md"),
    )

    customer_agent = create_react_agent(
        _model,
        tools=get_tools_for(AgentsTool.CUSTOMER),
        prompt=_load_md("customer_support.md"),
    )

    inventory_agent = create_react_agent(
        _model,
        tools=get_tools_for(AgentsTool.INVENTORY),
        prompt=_load_md("inventory.md"),
    )

    knowledge_agent = create_react_agent(
        _model,
        tools=get_tools_for(AgentsTool.KNOWLEDGE),
        prompt=_load_md("knowledge.md"),
    )

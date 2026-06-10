from pathlib import Path

from langchain.agents import create_agent
from langchain_openai import AzureChatOpenAI

from src.core.config import settings
from src.declarative.AgentSpec import AgentsTool, get_tools_for
from src.declarative.hitl_middleware import make_hitl_middleware
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
aggregator_agent = None
_model = None  # shared model instance exposed for other modules (e.g. workflow.py)


def init_agents() -> None:
    """Create all agent instances using tools already stored via store_tools()."""
    global orchestrator, sales_agent, customer_agent, inventory_agent, knowledge_agent, aggregator_agent, _model_heavy, _model_light # noqa E501

    _model_heavy = AzureChatOpenAI(
        azure_deployment=settings.azure_chat_flag_model,
        api_version=settings.azure_api_version,
        azure_endpoint=settings.azure_endpoint,
        api_key=settings.azure_api_key.get_secret_value() if settings.azure_api_key else None,
    )

    _model_light = AzureChatOpenAI(
        azure_deployment=settings.azure_chat_light_model,
        api_version=settings.azure_api_version,
        azure_endpoint=settings.azure_endpoint,
        api_key=settings.azure_api_key.get_secret_value() if settings.azure_api_key else None,
    )

    # AGENTS

    orchestrator = create_agent(
        _model_light,
        tools=get_tools_for(AgentsTool.ORCHESTRATOR),
        system_prompt=_load_md("orchestrator.md"),
        response_format=OrchestratorOutput,
    )

    # tools , middleware and finallt actual agents are created.
    _sales_tools = get_tools_for(AgentsTool.SALES)
    _sales_mw = make_hitl_middleware(_sales_tools)
    sales_agent = create_agent(
        _model_light,
        tools=_sales_tools,
        system_prompt=_load_md("sales.md"),
        middleware=[_sales_mw] if _sales_mw else [],
    )

    _customer_tools = get_tools_for(AgentsTool.CUSTOMER)
    _customer_mw = make_hitl_middleware(_customer_tools)
    customer_agent = create_agent(
        _model_light,
        tools=_customer_tools,
        system_prompt=_load_md("customer_support.md"),
        middleware=[_customer_mw] if _customer_mw else [],
    )

    _inventory_tools = get_tools_for(AgentsTool.INVENTORY)
    _inventory_mw = make_hitl_middleware(_inventory_tools)
    inventory_agent = create_agent(
        _model_light,
        tools=_inventory_tools,
        system_prompt=_load_md("inventory.md"),
        middleware=[_inventory_mw] if _inventory_mw else [],
    )

    _knowledge_tools = get_tools_for(AgentsTool.KNOWLEDGE)
    _knowledge_mw = make_hitl_middleware(_knowledge_tools)
    knowledge_agent = create_agent(
        _model_light,
        tools=_knowledge_tools,
        system_prompt=_load_md("knowledge.md"),
        middleware=[_knowledge_mw] if _knowledge_mw else [],
    )

    aggregator_agent = create_agent(
        _model_heavy,
        tools=[],
        system_prompt=_load_md("Aggregator.md"),
    )

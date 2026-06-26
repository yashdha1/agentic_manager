import os
from pathlib import Path

from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import AzureChatOpenAI

from src.core.config import settings
from src.declarative.AgentSpec import AgentsTool, get_tools_for
from src.models.AgentOutput import OrchestratorOutput

_AGENTS_DIR = Path(__file__).parent / "agents"


def _load_md(filename: str) -> str:
    return (_AGENTS_DIR / filename).read_text(encoding="utf-8")


# Module-level agent instances — None until init_agents() is called at startup.
orchestrator = None
aggregator_agent = None
_model_heavy = None
_model_light = None
_model_light_light = None


def init_agents() -> None:
    """Create all agent instances using tools already stored via store_tools()."""
    global orchestrator, aggregator_agent, _model_heavy, _model_light, _model_light_light

    _model_heavy = AzureChatOpenAI(
        azure_deployment=settings.azure_chat_flag_model,
        api_version=settings.azure_api_version,
        azure_endpoint=settings.azure_endpoint,
        api_key=settings.azure_api_key.get_secret_value(),
    )

    _model_light = AzureChatOpenAI(
        azure_deployment=settings.azure_chat_light_model,
        api_version=settings.azure_api_version,
        azure_endpoint=settings.azure_endpoint,
        api_key=settings.azure_api_key.get_secret_value(),
    )

    _model_light_light = ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        google_api_key=os.getenv("GEMINI_API_KEY"),
    )

    orchestrator = create_agent(
        _model_light,
        tools=get_tools_for(AgentsTool.ORCHESTRATOR),
        system_prompt=_load_md("orchestrator.md"),
        response_format=OrchestratorOutput,
    )

    aggregator_agent = create_agent(
        _model_heavy,
        tools=[],
        system_prompt=_load_md("Aggregator.md"),
    )

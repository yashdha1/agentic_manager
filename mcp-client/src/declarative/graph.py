from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import create_react_agent

from src.core.config import settings

graph = None  # compiled at startup via init_graph()


def init_graph(tools: list) -> None:
    global graph
    model = AzureChatOpenAI(
        azure_deployment=settings.azure_chat_model,
        api_version=settings.azure_api_version,
        azure_endpoint=settings.azure_endpoint,
        api_key=settings.azure_api_key.get_secret_value() if settings.azure_api_key else None,
    )
    graph = create_react_agent(model, tools)

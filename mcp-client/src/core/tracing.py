import os

from src.core.config import settings
from src.core.logger import logger


def configure_langsmith_tracing() -> bool:
    """Set LangSmith tracing env vars for the current process.

    Returns True when tracing is enabled.
    """
    enabled = bool(settings.langchain_tracing_v2)
    enabled_str = str(enabled).lower()

    # Support both legacy and current variable names.
    os.environ["LANGCHAIN_TRACING_V2"] = enabled_str
    os.environ["LANGSMITH_TRACING"] = enabled_str

    if settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key.get_secret_value()

    project = settings.langsmith_project
    if project:
        os.environ["LANGSMITH_PROJECT"] = project

    endpoint = settings.langsmith_endpoint
    if endpoint:
        os.environ["LANGSMITH_ENDPOINT"] = endpoint

    logger.info(
        "LangSmith tracing configured: "
        f"enabled={enabled}; project={project or '-'}; endpoint={endpoint or '-'}"
    )
    return enabled

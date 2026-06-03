from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    # MCP Server settings
    MCP_SERVER_HOST: str = "localhost"
    MCP_SERVER_PORT: int = 9000

    # LangSmith settings
    LANGSMITH_API_KEY: str
    PG_ASYNC_URL: str

    # MODEL SETTINGS
    AZURE_API_KEY: str
    AZURE_ENDPOINT: str
    AZURE_API_VERSION: str
    AZURE_EMBEDDING_MODEL: str
    AZURE_EMBEDDING_DIMENSIONS: int

    # Qdrant Settings
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333

    # Qdrant Collections
    KB_COLLECTION: str = "kb_collection"
    THREAD_COLLECTION: str = "thread_collection"
    RESOLVER_COLLECTION: str = "resolver_memory"


settings = Settings()

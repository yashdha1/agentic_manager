from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(_ENV_FILE), extra="ignore")

    # MCP Server settings
    MCP_SERVER_HOST: str = "localhost"
    MCP_SERVER_PORT: int = 9000

    # LangSmith settings
    LANGSMITH_API_KEY: str = ""

    # Postgres — individual fields (from .env); PG_ASYNC_URL is derived automatically
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "postgres"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    @computed_field  # type: ignore[prop-decorator]
    @property
    def PG_ASYNC_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

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
    KB_POLICY_COLLECTION: str = "kb_policy_collection"
    KB_MARKETING_COLLECTION: str = "kb_marketing_collection"
    KB_CAMPAIGN_COLLECTION: str = "kb_campaign_collection"
    THREAD_COLLECTION: str = "thread_collection"
    RESOLVER_COLLECTION: str = "resolver_memory"


settings = Settings()

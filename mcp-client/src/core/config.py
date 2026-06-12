from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    azure_api_key: SecretStr | None = Field(default=None, alias="AZURE_API_KEY")
    azure_api_version: str | None = Field(default=None, alias="AZURE_API_VERSION")
    azure_chat_flag_model: str | None = Field(default=None, alias="AZURE_CHAT_FLAG_MODEL")
    azure_chat_light_model: str | None = Field(default=None, alias="AZURE_CHAT_LIGHT_MODEL")
    azure_endpoint: str | None = Field(default=None, alias="AZURE_ENDPOINT")
    azure_embedding_model: str | None = Field(default=None, alias="AZURE_EMBEDDING_MODEL")
    azure_embedding_dimensions: int | None = Field(default=None, alias="AZURE_EMBEDDING_DIMENSIONS")

    langchain_tracing_v2: bool = Field(default=False, alias="LANGCHAIN_TRACING_V2")
    langsmith_api_key: SecretStr | None = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_project: str | None = Field(default=None, alias="LANGSMITH_PROJECT")
    langsmith_endpoint: str | None = Field(default=None, alias="LANGSMITH_ENDPOINT")

    qdrant_host: str = Field(default="http://localhost", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")
    langgraph_api_url: str = Field(default="http://localhost:2024", alias="LANGGRAPH_API_URL")

    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    # STM TTL in seconds (None = no expiry).  Default: 86400 s = 24 h.
    redis_stm_ttl: int | None = Field(default=86400, alias="REDIS_STM_TTL")

    mcp_server_url: str = Field(default="http://localhost:9000", alias="MCP_SERVER_URL")

    # PostgreSQL (same DB as mcp-server)
    postgres_user: str = Field(default="postgres", alias="POSTGRES_USER")
    postgres_password: str = Field(default="", alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(default="postgres", alias="POSTGRES_DB")
    postgres_host: str = Field(default="localhost", alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, alias="POSTGRES_PORT")

    # Qdrant thread collection (must match mcp-server THREAD_COLLECTION)
    qdrant_thread_collection: str = Field(default="thread_collection", alias="THREAD_COLLECTION")
    # Qdrant resolver collection (must match mcp-server RESOLVER_COLLECTION)
    qdrant_resolver_collection: str = Field(default="resolver_memory", alias="RESOLVER_COLLECTION")


settings = Settings()

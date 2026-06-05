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
    azure_chat_model: str | None = Field(default=None, alias="AZURE_CHAT_MODEL")
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

    mcp_server_url: str = Field(default="http://localhost:9000", alias="MCP_SERVER_URL")


settings = Settings()

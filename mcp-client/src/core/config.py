from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    azure_openai_api_key: SecretStr | None = Field(
        default=None, alias="AZURE_OPENAI_API_KEY"
    )
    azure_openai_api_version: str | None = Field(
        default=None, alias="AZURE_OPENAI_API_VERSION"
    )
    azure_openai_model: str | None = Field(default=None, alias="AZURE_OPENAI_MODEL")
    azure_openai_endpoint: str | None = Field(
        default=None, alias="AZURE_OPENAI_ENDPOINT"
    )
    azure_embedding_model: str | None = Field(
        default=None, alias="AZURE_EMBEDDING_MODEL"
    )

    langchain_tracing_v2: bool = Field(default=False, alias="LANGCHAIN_TRACING_V2")
    langsmith_api_key: SecretStr | None = Field(default=None, alias="LANGSMITH_API_KEY")
    langsmith_project: str | None = Field(default=None, alias="LANGSMITH_PROJECT")
    langsmith_endpoint: str | None = Field(default=None, alias="LANGSMITH_ENDPOINT")

    qdrant_host: str = Field(default="http://localhost", alias="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, alias="QDRANT_PORT")


settings = Settings()

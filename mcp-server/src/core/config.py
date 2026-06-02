from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # MCP Server settings
    MCP_SERVER_HOST: str = "localhost"
    MCP_SERVER_PORT: int = 9000

    # LangSmith settings
    LANGSMITH_API_KEY: str


settings = Settings()

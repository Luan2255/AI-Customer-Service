from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and the optional .env file."""

    # API metadata and route configuration.
    app_name: str = "AI Customer Service"
    environment: str = "development"
    api_v1_prefix: str = ""

    # Database connection used by SQLAlchemy and Alembic.
    database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/ai_customer_service"

    # Credentials and runtime limits for the OpenAI-compatible LLM endpoint.
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 30

    # Maximum number of previous messages included in each model request.
    conversation_history_limit: int = 20

    # Ignore unrelated environment variables so deployment environments can share a .env file.
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings instance for the lifetime of the process."""
    return Settings()
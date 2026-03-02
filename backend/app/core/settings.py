from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    app_name: str = "LegacyLens API"
    api_prefix: str = "/api"
    api_version: str = "0.1.0"
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    openai_api_key: str | None = None

    model_config = SettingsConfigDict(env_prefix="LEGACY_", env_file=".env", env_file_encoding="utf-8")

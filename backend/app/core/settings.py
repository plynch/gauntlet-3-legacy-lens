import json
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "LegacyLens API"
    api_prefix: str = "/api"
    api_version: str = "0.1.0"
    environment: str = "dev"
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:4173"]
    )
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    openai_api_key: str | None = None
    qdrant_collection: str = "legacylens_chunks"
    embedding_model: str = "text-embedding-3-small"
    generation_model: str = "gpt-4.1-mini"
    local_embedding_dimensions: int = 256
    query_top_k: int = 5
    max_context_characters: int = 9000
    source_directories: list[str] = Field(
        default_factory=lambda: ["backend/data/corpus", "data/corpus", "corpus"]
    )
    source_extensions: list[str] = Field(default_factory=lambda: [".cbl", ".cob", ".cpy", ".copy"])
    chunk_max_lines: int = 80
    chunk_overlap_lines: int = 16

    model_config = SettingsConfigDict(
        env_prefix="LEGACYLENS_",
        env_file=".env",
        env_file_encoding="utf-8",
    )

    @field_validator("allowed_origins", "source_directories", "source_extensions", mode="before")
    @classmethod
    def parse_list_value(cls, value: Any) -> Any:
        if not isinstance(value, str):
            return value

        stripped = value.strip()
        if not stripped:
            return []

        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass

        return [part.strip() for part in stripped.split(",") if part.strip()]

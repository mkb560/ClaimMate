from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AIConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    rag_model: str = "gpt-5.4-mini"
    rag_reasoning_effort: str = "xhigh"
    classification_model: str = "gpt-5.4-mini"
    classification_reasoning_effort: str = "xhigh"
    embedding_model: str = "text-embedding-3-large"
    database_url: str = ""

    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    s3_bucket_name: str = ""
    aws_region: str = "us-east-1"

    vector_table_name: str = "vector_documents"
    vector_dimensions: int = 1536

    kb_a_chunk_size: int = 500
    kb_a_chunk_overlap: int = 50
    kb_b_chunk_size: int = 250
    kb_b_chunk_overlap: int = 30
    rag_top_k_per_source: int = 4
    deadline_alert_threshold_days: int = 5
    deadline_alert_cooldown_hours: int = 24

    @field_validator("openai_base_url")
    @classmethod
    def normalize_base_url(cls, value: str) -> str:
        return value.rstrip("/")

    def require_openai(self) -> None:
        if not self.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for OpenAI-powered AI calls.")

    def require_database(self) -> None:
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is required for database-backed AI operations.")


@lru_cache(maxsize=1)
def get_ai_config() -> AIConfig:
    return AIConfig()


ai_config = get_ai_config()

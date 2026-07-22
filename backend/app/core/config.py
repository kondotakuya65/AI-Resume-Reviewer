from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Resume Reviewer"
    environment: str = "development"
    api_prefix: str = "/api"
    cors_origins: str = "http://localhost:3000"

    database_url: str = "postgresql+psycopg2://resume:resume@localhost:5432/resume_reviewer"

    llm_provider: Literal["ollama", "openai", "anthropic"] = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-latest"

    storage_backend: Literal["local", "s3"] = "local"
    upload_dir: str = "./uploads"
    aws_s3_bucket: str = ""
    aws_region: str = "us-east-1"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""

    prompt_version: str = "v1"
    guest_cookie_name: str = "guest_token"
    max_upload_mb: int = 10

    disclaimer: str = (
        "This analysis is AI-generated guidance and does not guarantee interviews, "
        "employment, or acceptance by applicant tracking systems."
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

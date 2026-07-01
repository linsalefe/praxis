"""Configuração central (pydantic-settings)."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).resolve().parent.parent / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # DB
    database_url: str = Field(alias="DATABASE_URL")

    # Segurança
    field_key: str = Field(alias="PRAXIS_FIELD_KEY")
    jwt_secret: str = Field(alias="PRAXIS_JWT_SECRET")
    jwt_alg: str = Field(default="HS256", alias="PRAXIS_JWT_ALG")
    jwt_ttl_minutes: int = Field(default=60, alias="PRAXIS_JWT_TTL_MINUTES")
    totp_issuer: str = Field(default="Praxis by CENAT", alias="PRAXIS_TOTP_ISSUER")

    # Sofia (RAG)
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    llm_model: str = Field(default="gpt-5.1-mini", alias="PRAXIS_LLM_MODEL")
    embed_model: str = Field(default="text-embedding-3-small", alias="PRAXIS_EMBED_MODEL")
    embed_dim: int = Field(default=1536, alias="PRAXIS_EMBED_DIM")
    rag_topk: int = Field(default=6, alias="PRAXIS_RAG_TOPK")
    rag_sim_min: float = Field(default=0.28, alias="PRAXIS_RAG_SIM_MIN")
    sofia_send_patient: bool = Field(default=False, alias="PRAXIS_SOFIA_SEND_PATIENT")

    # Scribe
    transcriber: str = Field(default="openai", alias="PRAXIS_TRANSCRIBER")
    transc_model: str = Field(default="gpt-4o-mini-transcribe", alias="PRAXIS_TRANSC_MODEL")
    scribe_audio_dir: str = Field(default="/opt/praxis/backend/uploads/audio", alias="PRAXIS_SCRIBE_AUDIO_DIR")
    scribe_max_mb: int = Field(default=25, alias="PRAXIS_SCRIBE_MAX_MB")

    # App
    env: str = Field(default="dev", alias="PRAXIS_ENV")
    bind_host: str = Field(default="127.0.0.1", alias="PRAXIS_BIND_HOST")
    bind_port: int = Field(default=8040, alias="PRAXIS_BIND_PORT")
    cors_origins: str = Field(
        default="http://127.0.0.1:3040,http://localhost:3040",
        alias="PRAXIS_CORS_ORIGINS",
    )

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "local"
    dev_auth_enabled: bool = True
    database_url: str = "sqlite+aiosqlite:///./rsi.db"
    redis_url: str = "redis://localhost:6379/0"
    nats_url: str = "nats://localhost:4222"
    temporal_address: str = "localhost:7233"
    qdrant_url: str = "http://localhost:6333"
    s3_endpoint: str = "http://localhost:9000"
    s3_bucket: str = "rsi-artifacts"
    s3_access_key: str = "localminio"
    s3_secret_key: str = "localminiosecret"
    policy_signing_key: str = "change-me"
    jwt_secret: str = "change-me"
    oidc_issuer: str = ""
    oidc_audience: str = "conversational-agent-rsi"
    model_gateway_url: str = ""
    model_gateway_api_key: str = ""
    default_model: str = "fake/deterministic"
    default_embedding_model: str = "fake/hash-embedding"
    default_tenant_budget_usd: float = 25.0
    default_run_budget_usd: float = 5.0
    default_max_turns: int = 50
    cors_origins: str = "http://localhost:3000"
    log_raw_content: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.cors_origins.split(",") if x.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()

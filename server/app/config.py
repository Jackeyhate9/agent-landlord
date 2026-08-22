from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    sqlite_path: str = ":memory:"
    avatar_dir: str = "./data/avatars"
    postgres_url: str = ""
    redis_url: str = ""
    session_secret: str = Field(default="development-only-change-this-secret-32", min_length=32)
    initial_arena_tokens: int = 10_000
    max_multiplier: int = 8
    max_table_win_streak: int = 10
    agent_decision_timeout_ms: int = 8_000
    broadcast_delay_seconds: float = 30.0
    admin_password: str = "change-me"
    max_payload_bytes: int = 65_536
    rate_limit_per_minute: int = 600
    join_code_ttl_seconds: int = 600
    public_api_url: str = ""

    def validate_production_secrets(self) -> None:
        if self.app_env.lower() in {"production", "prod"}:
            weak_secrets = {"development-only-change-this-secret-32", "replace-with-at-least-32-random-characters"}
            weak_admins = {"change-me", ""}
            if self.session_secret in weak_secrets or len(self.session_secret) < 32:
                raise ValueError("SESSION_SECRET must be replaced in production (≥32 random characters)")
            if self.admin_password in weak_admins:
                raise ValueError("ADMIN_PASSWORD must be replaced in production")


@lru_cache
def get_settings() -> Settings:
    return Settings()

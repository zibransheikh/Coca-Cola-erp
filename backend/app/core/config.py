from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://dms:dms@localhost:5432/dms"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    # Comma-separated, not a JSON list, so a plain .env value like
    # "http://localhost:5173,https://your-site.netlify.app" works without
    # needing pydantic-settings' JSON-list parsing for env vars.
    cors_origins: str = "http://localhost:5173"

    @field_validator("database_url")
    @classmethod
    def _use_psycopg3_driver(cls, v: str) -> str:
        # Hosted Postgres providers (Neon, Render, Supabase, ...) hand out
        # bare "postgresql://" connection strings, which makes SQLAlchemy
        # default to psycopg2 — not a dependency here, only psycopg3 is.
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+psycopg://", 1)
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()

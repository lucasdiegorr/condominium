"""Application settings loaded from environment variables / .env file."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Condominium Management API."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Condominium Management API"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://cond:cond_pass@localhost:5432/condominium"

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    identity_token_ttl_minutes: int = 60
    scoped_token_ttl_minutes: int = 20

    # Seed (first run)
    seed_admin_email: str = "admin@example.com"
    seed_admin_password: str = "admin123456"


@lru_cache
def get_settings() -> Settings:
    return Settings()

"""Application settings loaded from environment variables / .env file."""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    """Runtime configuration for the Condominium Management API."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Condominium Management API"
    debug: bool = False

    # Database. The URL is composed from individual POSTGRES_* components so a
    # password with special characters (% @ : ...) is percent-encoded correctly
    # for every consumer (alembic configparser, SQLAlchemy/asyncpg). An explicit
    # DATABASE_URL still takes precedence.
    database_url: str | None = None
    postgres_user: str = "cond"
    postgres_password: str = "cond_pass"
    postgres_db: str = "condominium"
    postgres_host: str = "localhost"
    postgres_host: str = "localhost"
    postgres_port: int = 5432

    # JWT
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    identity_token_ttl_minutes: int = 60
    scoped_token_ttl_minutes: int = 20

    # Seed (first run)
    seed_admin_email: str = "admin@example.com"
    seed_admin_password: str = "admin123456"

    @model_validator(mode="after")
    def _compose_database_url(self) -> "Settings":
        """Build the database URL from POSTGRES_* when DATABASE_URL is absent."""
        if not self.database_url:
            self.database_url = URL.create(
                drivername="postgresql+asyncpg",
                username=self.postgres_user,
                password=self.postgres_password,
                host=self.postgres_host,
                port=self.postgres_port,
                database=self.postgres_db,
            ).render_as_string(hide_password=False)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

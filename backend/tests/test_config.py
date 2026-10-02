"""Settings — database URL composition and percent-encoding."""

from sqlalchemy.engine import make_url

from app.config import Settings


def _settings(monkeypatch, **kwargs):
    """Build Settings with POSTGRES_* env vars and no DATABASE_URL."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("POSTGRES_USER", "cond")
    monkeypatch.setenv("POSTGRES_PASSWORD", "cond_pass")
    monkeypatch.setenv("POSTGRES_DB", "condominium")
    monkeypatch.setenv("POSTGRES_HOST", "localhost")
    monkeypatch.setenv("POSTGRES_PORT", "5432")
    return Settings(_env_file=None, **kwargs)


def test_database_url_is_composed_from_components(monkeypatch) -> None:
    settings = _settings(monkeypatch)
    assert settings.database_url == "postgresql+asyncpg://cond:cond_pass@localhost:5432/condominium"


def test_special_characters_in_password_are_percent_encoded(monkeypatch) -> None:
    settings = _settings(
        monkeypatch,
        postgres_user="condominium-user",
        postgres_password="ABYNz%gg3@YiD4F",
        postgres_host="postgres",
    )
    # The composed URL is safe for configparser ("%" escaped) and unambiguous
    # for URL parsing ("@" encoded).
    assert "%25" in settings.database_url
    assert "%40" in settings.database_url
    parsed = make_url(settings.database_url)
    assert parsed.username == "condominium-user"
    assert parsed.password == "ABYNz%gg3@YiD4F"
    assert parsed.host == "postgres"


def test_explicit_database_url_takes_precedence(monkeypatch) -> None:
    explicit = "postgresql+asyncpg://other:other@db:5432/other"
    settings = _settings(monkeypatch, database_url=explicit)
    assert settings.database_url == explicit


def test_url_survives_alembic_configparser_round_trip(monkeypatch) -> None:
    """Regression: alembic set_main_option crashed with 'invalid interpolation
    syntax' when the password contained '%' (even percent-encoded)."""
    from configparser import ConfigParser

    settings = _settings(
        monkeypatch,
        postgres_user="condominium-user",
        postgres_password="ABYNz%gg3@YiD4F",
        postgres_host="postgres",
    )
    # Same escaping alembic/env.py applies before configparser.set().
    value = settings.database_url.replace("%", "%%")
    cp = ConfigParser()
    cp.add_section("alembic")
    cp.set("alembic", "sqlalchemy.url", value)  # used to raise ValueError
    restored = cp.get("alembic", "sqlalchemy.url")
    assert restored == settings.database_url
    parsed = make_url(restored)
    assert parsed.host == "postgres"
    assert parsed.password == "ABYNz%gg3@YiD4F"

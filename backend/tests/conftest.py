"""Test infrastructure.

Sets environment variables BEFORE importing the application, prepares an isolated
PostgreSQL test database (migrations + seed), and provides an async HTTP client.
"""

import asyncio
import os
import subprocess
import sys
from pathlib import Path

import asyncpg
import httpx
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
TEST_DB = "condominium_test"
DB_USER = "cond"
DB_PASSWORD = "cond_pass"
DB_HOST = "localhost"
DB_PORT = "5432"

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"

os.environ["DATABASE_URL"] = (
    f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{TEST_DB}"
)
os.environ["JWT_SECRET"] = "test-secret-0123456789abcdefghijklmnopqrstuvwxyz"
os.environ["SEED_ADMIN_EMAIL"] = ADMIN_EMAIL
os.environ["SEED_ADMIN_PASSWORD"] = ADMIN_PASSWORD

from app.main import app  # noqa: E402  (after env setup)


async def _connect_admin() -> asyncpg.Connection:
    return await asyncpg.connect(
        user=DB_USER, password=DB_PASSWORD, host=DB_HOST, port=DB_PORT, database="postgres"
    )


async def _drop_test_db() -> None:
    conn = await _connect_admin()
    try:
        await conn.execute(f"DROP DATABASE IF EXISTS {TEST_DB} WITH (FORCE)")
    finally:
        await conn.close()


async def _create_test_db() -> None:
    conn = await _connect_admin()
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB)
        if not exists:
            await conn.execute(f"CREATE DATABASE {TEST_DB}")
    finally:
        await conn.close()


def _run_backend_command(*args: str) -> None:
    result = subprocess.run(
        [sys.executable, *args],
        cwd=BACKEND_DIR,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Command {' '.join(args)} failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
        )


@pytest.fixture(scope="session", autouse=True)
def database() -> None:
    """Reset the test database and apply migrations + seed once per session."""
    asyncio.run(_drop_test_db())
    asyncio.run(_create_test_db())
    _run_backend_command("-m", "alembic", "upgrade", "head")
    _run_backend_command("-m", "app.seed")


@pytest.fixture
async def client() -> httpx.AsyncClient:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


async def admin_identity_token(client: httpx.AsyncClient) -> str:
    """Helper: log in as the seeded global administrator."""
    response = await client.post(
        "/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return response.json()["token"]

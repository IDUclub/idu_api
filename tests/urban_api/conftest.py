"""All configurations and fixtures for Urban API integration tests.

This setup provides:
- PostgreSQL database with Alembic migrations
- FastAPI application in ASGI test mode (no subprocess)
- Async HTTP client for integration testing
"""

import os
from pathlib import Path

import pytest
import pytest_asyncio
import structlog
from alembic import command
from alembic.config import Config
from asgi_lifespan import LifespanManager
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient

from idu_api.common.db.config import MultipleDBsConfig
from idu_api.urban_api.config import UrbanAPIConfig
from idu_api.urban_api.fastapi_init import get_app
from tests.urban_api.helpers import *  # noqa: F401,F403

logger = structlog.get_logger("test")
load_dotenv(dotenv_path="urban_api/.env")


# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def database() -> MultipleDBsConfig:
    """
    Provide database configuration for integration tests.

    Loads configuration from TEST_CONFIG_PATH and applies Alembic migrations
    before any tests are executed.
    """
    if "TEST_CONFIG_PATH" not in os.environ:
        pytest.skip("Database for integration tests is not configured")

    config = UrbanAPIConfig.load(os.environ["TEST_CONFIG_PATH"])

    run_migrations(config.db)
    return config.db


def run_migrations(database: MultipleDBsConfig) -> None:
    """
    Apply Alembic migrations to the test database.

    This ensures schema is up-to-date before running tests.
    """
    dsn = (
        f"postgresql+asyncpg://{database.master.user}:"
        f"{database.master.password.get_secret_value()}"
        f"@{database.master.host}:{database.master.port}/"
        f"{database.master.database}"
    )

    alembic_dir = Path(__file__).resolve().parent.parent.parent / "idu_api" / "common" / "db"

    alembic_cfg = Config(str(alembic_dir / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(alembic_dir / "migrator"))
    alembic_cfg.set_main_option("sqlalchemy.url", dsn)

    try:
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        pytest.fail(f"Error during migration setup: {str(e)}")


# ---------------------------------------------------------------------------
# Application config
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def config(database) -> UrbanAPIConfig:
    """
    Build application configuration for tests.

    Reuses production config file but overrides database settings
    with test database.
    """
    base = UrbanAPIConfig.load(os.environ["TEST_CONFIG_PATH"])
    base.db = database
    base.app.uvicorn.reload = False
    return base


# ---------------------------------------------------------------------------
# FastAPI application (ASGI mode)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="function")
def app(config):
    """
    Create FastAPI application instance for testing.

    Application is run in ASGI mode without network or subprocess.
    """
    app = get_app(config=config)
    return app


# ---------------------------------------------------------------------------
# Async HTTP client
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def client(app):
    """
    Async HTTP client bound to FastAPI ASGI application.

    This replaces real HTTP server and allows fast in-memory requests.
    """
    async with LifespanManager(app):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as ac:
            yield ac


# ---------------------------------------------------------------------------
# Smoke test fixture (prevents silent app misconfiguration)
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def _smoke_test(client: AsyncClient):
    """
    Basic smoke test to ensure application starts correctly.

    Fails fast if app routing or startup configuration is broken.
    """
    response = await client.get("/health_check/ping")

    assert response.status_code == 200, "Application failed smoke test: /health_check/ping is not healthy"

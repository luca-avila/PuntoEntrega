import os
import shutil
import tempfile
from pathlib import Path

import pytest_asyncio
import pytest
from httpx import ASGITransport, AsyncClient

# Set required env vars before importing the app so Settings validation passes.
# We force an isolated DB for tests by default so no real/dev DB is touched.
_temp_test_db_dir: Path | None = None
_test_database_url = os.getenv("TEST_DATABASE_URL")
if _test_database_url:
    os.environ["DATABASE_URL"] = _test_database_url
else:
    _temp_test_db_dir = Path(tempfile.mkdtemp(prefix="puntoentrega-tests-"))
    _test_db_path = _temp_test_db_dir / "test.db"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_test_db_path}"

os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters-long")
os.environ.setdefault("RESEND_API_KEY", "test-resend-api-key")
os.environ.setdefault("EMAIL_FROM", "PuntoEntrega <test@example.com>")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("LOG_LEVEL", "INFO")
os.environ.setdefault("LOG_REQUESTS", "false")
os.environ.setdefault("CORS_ORIGINS", '["http://localhost:5173"]')
os.environ.setdefault("FRONTEND_URL", "http://localhost:5173")

from app.api import app
from core.config import settings
from core.db import engine
from features.auth.models import Base


@pytest.fixture(autouse=True)
def fast_notification_outbox_retries(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(settings, "NOTIFICATION_OUTBOX_RETRY_BASE_DELAY_SECONDS", 0.0)


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    """Create tables before each test and drop them after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def cleanup_test_database_artifacts():
    """Dispose DB connections and remove temporary DB artifacts after the test session."""
    yield
    await engine.dispose()
    if _temp_test_db_dir is not None:
        shutil.rmtree(_temp_test_db_dir, ignore_errors=True)


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="https://test") as ac:
        yield ac

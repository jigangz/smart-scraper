import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import patch

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


@pytest_asyncio.fixture(scope="function")
async def async_client(tmp_path):
    """HTTP test client with isolated in-file SQLite database."""
    from app.db.database import Base, get_db
    from app.main import app

    db_url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    async def mock_init_db():
        pass

    with patch("app.main.init_db", mock_init_db), \
         patch("app.scraper.scheduler.JobScheduler.start"), \
         patch("app.scraper.scheduler.JobScheduler.stop"):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            client._test_session_factory = session_factory
            yield client

    app.dependency_overrides.clear()
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_job(async_client):
    """Pre-created job in the test database via the API."""
    response = await async_client.post("/api/jobs", json={
        "name": "Test Job",
        "url": "https://example.com",
        "selectors": {"title": "h1"},
    })
    assert response.status_code == 201
    return response.json()

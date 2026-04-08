"""Tests for JS interaction support in ScrapingEngine (T-007)."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from app.scraper.engine import _execute_interactions, ScrapingEngine


# ---------------------------------------------------------------------------
# Unit tests for _execute_interactions (module-level function)
# ---------------------------------------------------------------------------

def test_execute_interactions_click():
    """click action calls execute_js with querySelector click."""
    page = MagicMock()
    interactions = [{"action": "click", "selector": ".btn", "repeat": 1, "wait_ms": 0}]
    _execute_interactions(page, interactions)

    page.execute_js.assert_called_once()
    call_arg = page.execute_js.call_args[0][0]
    assert ".btn" in call_arg
    assert "click" in call_arg


def test_execute_interactions_scroll():
    """scroll action calls execute_js with scrollTo."""
    page = MagicMock()
    interactions = [{"action": "scroll", "repeat": 1, "wait_ms": 0}]
    _execute_interactions(page, interactions)

    page.execute_js.assert_called_once()
    call_arg = page.execute_js.call_args[0][0]
    assert "scrollTo" in call_arg or "scroll" in call_arg.lower()


def test_execute_interactions_type():
    """type action calls execute_js with value assignment."""
    page = MagicMock()
    interactions = [
        {"action": "type", "selector": "#search", "value": "hello", "repeat": 1, "wait_ms": 0}
    ]
    _execute_interactions(page, interactions)

    page.execute_js.assert_called_once()
    call_arg = page.execute_js.call_args[0][0]
    assert "#search" in call_arg
    assert "hello" in call_arg


def test_execute_interactions_select():
    """select action calls execute_js to set option value."""
    page = MagicMock()
    interactions = [
        {"action": "select", "selector": "#dropdown", "value": "opt2", "repeat": 1, "wait_ms": 0}
    ]
    _execute_interactions(page, interactions)

    page.execute_js.assert_called_once()
    call_arg = page.execute_js.call_args[0][0]
    assert "#dropdown" in call_arg
    assert "opt2" in call_arg


def test_execute_interactions_wait_for_selector():
    """wait action calls execute_js with selector check."""
    page = MagicMock()
    interactions = [{"action": "wait", "selector": ".loaded", "repeat": 1, "wait_ms": 0}]
    _execute_interactions(page, interactions)

    page.execute_js.assert_called_once()
    call_arg = page.execute_js.call_args[0][0]
    assert ".loaded" in call_arg


def test_execute_interactions_repeat():
    """repeat > 1 causes execute_js to be called multiple times."""
    page = MagicMock()
    interactions = [{"action": "scroll", "repeat": 3, "wait_ms": 0}]
    _execute_interactions(page, interactions)

    assert page.execute_js.call_count == 3


def test_execute_interactions_wait_ms_sleeps():
    """wait_ms > 0 triggers a sleep between interactions."""
    page = MagicMock()
    interactions = [{"action": "scroll", "repeat": 1, "wait_ms": 50}]

    with patch("app.scraper.engine.time.sleep") as mock_sleep:
        _execute_interactions(page, interactions)
        mock_sleep.assert_called_once_with(0.05)


def test_execute_interactions_no_execute_js_for_unknown_action():
    """Unknown action does not call execute_js."""
    page = MagicMock()
    interactions = [{"action": "unknown_action", "repeat": 1, "wait_ms": 0}]
    _execute_interactions(page, interactions)

    page.execute_js.assert_not_called()


# ---------------------------------------------------------------------------
# Integration tests via the API (schema + DB storage)
# ---------------------------------------------------------------------------

async def test_create_job_with_interactions(async_client):
    """POST /api/jobs stores interaction steps in the DB."""
    response = await async_client.post("/api/jobs", json={
        "name": "Interaction Job",
        "url": "https://example.com",
        "selectors": {"title": "h1"},
        "mode": "dynamic",
        "interactions": [
            {"action": "scroll"},
            {"action": "click", "selector": ".load-more"},
        ],
    })
    assert response.status_code == 201
    data = response.json()
    assert data["interactions"] is not None
    assert len(data["interactions"]) == 2
    assert data["interactions"][0]["action"] == "scroll"
    assert data["interactions"][1]["action"] == "click"


async def test_create_job_without_interactions(async_client):
    """POST /api/jobs works without interactions field (backward compatible)."""
    response = await async_client.post("/api/jobs", json={
        "name": "Plain Job",
        "url": "https://example.com",
        "selectors": {"title": "h1"},
    })
    assert response.status_code == 201
    data = response.json()
    assert data.get("interactions") is None


async def test_get_job_returns_interactions(async_client):
    """GET /api/jobs/{id} includes interactions in the response."""
    create_resp = await async_client.post("/api/jobs", json={
        "name": "Fetch Job",
        "url": "https://example.com",
        "selectors": {"title": "h1"},
        "mode": "stealth",
        "interactions": [{"action": "wait", "selector": "#content"}],
    })
    assert create_resp.status_code == 201
    job_id = create_resp.json()["id"]

    get_resp = await async_client.get(f"/api/jobs/{job_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["interactions"] is not None
    assert data["interactions"][0]["action"] == "wait"
    assert data["interactions"][0]["selector"] == "#content"


async def test_scrape_with_mode_fast_ignores_interactions():
    """fast mode does not invoke _execute_interactions even if interactions provided."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    import tempfile, os

    tmp = tempfile.mktemp(suffix=".db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp}", echo=False)
    from app.db.database import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        scraper = ScrapingEngine(job_id=1, db_session=session)
        mock_page = MagicMock()
        mock_page.css.return_value = []

        interactions = [{"action": "click", "selector": ".btn"}]

        with patch("app.scraper.engine._scrapling_fetch", return_value=mock_page):
            from app.scraper.anti_detect import AntiDetection
            anti = AntiDetection({"min_delay": 0, "max_delay": 0, "max_retries": 1})
            # fast mode: interactions must NOT be executed
            await scraper.scrape_with_mode(
                "https://example.com", {"title": "h1"}, "fast", anti, interactions
            )

        # execute_js should NOT have been called (fast mode ignores interactions)
        mock_page.execute_js.assert_not_called()

    await engine.dispose()
    if os.path.exists(tmp):
        os.remove(tmp)


async def test_scrape_with_mode_dynamic_executes_interactions():
    """dynamic mode calls _execute_interactions on the page object."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    import tempfile, os

    tmp = tempfile.mktemp(suffix=".db")
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp}", echo=False)
    from app.db.database import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as session:
        scraper = ScrapingEngine(job_id=1, db_session=session)
        mock_page = MagicMock()
        mock_page.css.return_value = []

        interactions = [{"action": "scroll", "repeat": 1, "wait_ms": 0}]

        with patch("app.scraper.engine._scrapling_fetch", return_value=mock_page):
            from app.scraper.anti_detect import AntiDetection
            anti = AntiDetection({"min_delay": 0, "max_delay": 0, "max_retries": 1})
            await scraper.scrape_with_mode(
                "https://example.com", {"title": "h1"}, "dynamic", anti, interactions
            )

        # execute_js should have been called (dynamic mode uses interactions)
        mock_page.execute_js.assert_called_once()

    await engine.dispose()
    if os.path.exists(tmp):
        os.remove(tmp)

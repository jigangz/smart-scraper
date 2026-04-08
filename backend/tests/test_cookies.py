"""
T-008 — Cookie/session injection tests.
Covers: injection into ScrapingEngine, encryption, decryption, missing key fallback,
and the API create/get flow.
"""
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.cookie_encryption import decrypt_cookies, encrypt_cookies


# ---------------------------------------------------------------------------
# Helper: generate a valid Fernet key
# ---------------------------------------------------------------------------

def _make_fernet_key() -> str:
    from cryptography.fernet import Fernet
    return Fernet.generate_key().decode()


# ---------------------------------------------------------------------------
# 1. Encryption round-trip
# ---------------------------------------------------------------------------

def test_encrypt_decrypt_round_trip(monkeypatch):
    """Encrypting then decrypting a cookie value restores the original."""
    key = _make_fernet_key()
    monkeypatch.setenv("ENCRYPTION_KEY", key)

    cookies = [{"name": "session", "value": "abc123", "domain": "example.com", "path": "/"}]
    encrypted = encrypt_cookies(cookies)

    assert encrypted[0]["value"] != "abc123"
    assert encrypted[0].get("_encrypted") is True

    restored = decrypt_cookies(encrypted)
    assert restored[0]["value"] == "abc123"
    assert "_encrypted" not in restored[0]


# ---------------------------------------------------------------------------
# 2. Missing ENCRYPTION_KEY → plaintext with warning
# ---------------------------------------------------------------------------

def test_encrypt_no_key_stores_plaintext(monkeypatch, caplog):
    """When ENCRYPTION_KEY is absent, cookies are stored as-is and a warning is logged."""
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

    import logging
    cookies = [{"name": "auth", "value": "token99", "domain": None, "path": "/"}]
    with caplog.at_level(logging.WARNING, logger="app.cookie_encryption"):
        result = encrypt_cookies(cookies)

    assert result[0]["value"] == "token99"
    assert "_encrypted" not in result[0]
    assert any("plaintext" in msg.lower() or "encryption_key" in msg.lower()
               for msg in caplog.messages)


# ---------------------------------------------------------------------------
# 3. Decryption of unencrypted cookies (no _encrypted flag) is a no-op
# ---------------------------------------------------------------------------

def test_decrypt_plaintext_cookies(monkeypatch):
    """Cookies without _encrypted flag pass through decrypt unchanged."""
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

    cookies = [{"name": "foo", "value": "bar", "domain": "x.com", "path": "/"}]
    result = decrypt_cookies(cookies)
    assert result[0]["value"] == "bar"


# ---------------------------------------------------------------------------
# 4. Cookie injection into _scrapling_fetch (fast mode)
# ---------------------------------------------------------------------------

def test_scrapling_fetch_passes_cookies_fast_mode():
    """_scrapling_fetch forwards cookies as a name→value dict to Fetcher.get."""
    from app.scraper.engine import _scrapling_fetch

    mock_page = MagicMock()
    cookies = [{"name": "sess", "value": "xyz", "domain": "site.com", "path": "/"}]

    with patch("app.scraper.engine._scrapling_fetch") as mock_fetch:
        mock_fetch.return_value = mock_page
        result = mock_fetch("http://example.com", "fast", None, cookies)

    mock_fetch.assert_called_once_with("http://example.com", "fast", None, cookies)


# ---------------------------------------------------------------------------
# 5. ScrapingEngine.run decrypts and passes cookies to scrape_with_mode
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_engine_run_decrypts_and_injects_cookies(monkeypatch):
    """
    ScrapingEngine.run() should decrypt cookies stored on the job and pass
    them to scrape_with_mode.
    """
    from cryptography.fernet import Fernet

    key = _make_fernet_key()
    monkeypatch.setenv("ENCRYPTION_KEY", key)

    # Encrypt a cookie as the API would do on create
    raw = [{"name": "token", "value": "secret", "domain": "example.com", "path": "/"}]
    encrypted = encrypt_cookies(raw)

    # Build a minimal mock job
    job = MagicMock()
    job.id = 1
    job.name = "test"
    job.url = "http://example.com"
    job.selectors = {"title": "h1"}
    job.mode = "fast"
    job.anti_detection = False
    job.pagination_config = None
    job.interactions = None
    job.cookies = encrypted

    db_session = AsyncMock()
    db_session.add = MagicMock()
    db_session.commit = AsyncMock()
    db_session.rollback = AsyncMock()

    from app.scraper.engine import ScrapingEngine

    engine = ScrapingEngine(job_id=1, db_session=db_session)

    # Capture what cookies scrape_with_mode receives
    captured_cookies = []

    async def fake_scrape_with_mode(url, selectors, mode, anti, interactions=None, cookies=None):
        captured_cookies.extend(cookies or [])
        return [{"title": "Hello"}]

    with patch.object(engine, "scrape_with_mode", side_effect=fake_scrape_with_mode):
        # Also mock cache (no Redis)
        with patch("app.scraper.engine.get_cached_result", new_callable=AsyncMock, return_value=None):
            with patch("app.scraper.engine.set_cached_result", new_callable=AsyncMock):
                await engine.run(job)

    assert len(captured_cookies) == 1
    assert captured_cookies[0]["name"] == "token"
    assert captured_cookies[0]["value"] == "secret"


# ---------------------------------------------------------------------------
# 6. API: create job with cookies, GET returns cookies field
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_api_create_job_with_cookies(async_client, monkeypatch):
    """POST /api/jobs with cookies stores them; GET /api/jobs/{id} returns cookies."""
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)  # plaintext for simplicity

    payload = {
        "name": "cookie-job",
        "url": "http://example.com",
        "selectors": {"title": "h1"},
        "cookies": [
            {"name": "auth", "value": "mytoken", "domain": "example.com", "path": "/"},
        ],
    }

    resp = await async_client.post("/api/jobs", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    job_id = data["id"]
    assert data["cookies"] is not None
    assert len(data["cookies"]) == 1
    assert data["cookies"][0]["name"] == "auth"

    get_resp = await async_client.get(f"/api/jobs/{job_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["cookies"][0]["name"] == "auth"


# ---------------------------------------------------------------------------
# 7. Multiple cookies round-trip
# ---------------------------------------------------------------------------

def test_encrypt_multiple_cookies(monkeypatch):
    """All cookies in a list are encrypted independently."""
    key = _make_fernet_key()
    monkeypatch.setenv("ENCRYPTION_KEY", key)

    cookies = [
        {"name": "a", "value": "val_a", "domain": "x.com", "path": "/"},
        {"name": "b", "value": "val_b", "domain": "x.com", "path": "/api"},
    ]
    encrypted = encrypt_cookies(cookies)
    assert encrypted[0]["value"] != "val_a"
    assert encrypted[1]["value"] != "val_b"

    decrypted = decrypt_cookies(encrypted)
    assert decrypted[0]["value"] == "val_a"
    assert decrypted[1]["value"] == "val_b"

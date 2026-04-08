"""Tests for T-009: LLM auto-selector discovery."""
from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from fakeredis.aioredis import FakeRedis

from app.auto_discover import (
    _get_domain,
    _sample_extract,
    _truncate_html,
    auto_discover_selectors,
)

# ---------------------------------------------------------------------------
# Fixtures / constants
# ---------------------------------------------------------------------------

SAMPLE_HTML = """
<html>
<body>
  <h1 class="title">Test Title</h1>
  <p class="content">Test content paragraph.</p>
  <a class="link" href="/page1">Link 1</a>
  <a class="link" href="/page2">Link 2</a>
</body>
</html>
"""

LLM_RESPONSE = {
    "selectors": {
        "title": ".title",
        "content": ".content",
        "links": ".link",
    },
    "description": "Extracts title, content, and links from the page.",
}


# ---------------------------------------------------------------------------
# Unit tests — pure functions
# ---------------------------------------------------------------------------


def test_get_domain():
    assert _get_domain("https://example.com/some/path?q=1") == "example.com"
    assert _get_domain("http://sub.domain.org:8080/page") == "sub.domain.org:8080"


def test_truncate_html_within_limit():
    html = "a" * 100
    assert _truncate_html(html) == html


def test_truncate_html_exceeds_limit():
    html = "x" * 40000
    result = _truncate_html(html)
    assert len(result) == 32000


def test_truncate_html_custom_limit():
    html = "y" * 500
    result = _truncate_html(html, max_chars=200)
    assert len(result) == 200


def test_sample_extract_extracts_text():
    selectors = {"title": ".title", "links": ".link"}
    samples = _sample_extract(SAMPLE_HTML, selectors)
    assert samples["title"] == ["Test Title"]
    assert "Link 1" in samples["links"]
    assert "Link 2" in samples["links"]


def test_sample_extract_missing_selector_returns_empty():
    selectors = {"missing": ".nonexistent-class-xyz"}
    samples = _sample_extract(SAMPLE_HTML, selectors)
    assert samples["missing"] == []


def test_sample_extract_limits_to_three():
    html = "<html><body>" + "".join(
        f'<p class="item">Item {i}</p>' for i in range(10)
    ) + "</body></html>"
    samples = _sample_extract(html, {"items": ".item"})
    assert len(samples["items"]) == 3


# ---------------------------------------------------------------------------
# Async integration tests — mock _fetch_html + _call_groq
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_auto_discover_returns_selectors_and_samples():
    """Full flow without Redis: fetch → LLM → extract → return."""
    with patch("app.auto_discover._fetch_html", return_value=SAMPLE_HTML), \
         patch("app.auto_discover._call_groq", return_value=LLM_RESPONSE):
        result = await auto_discover_selectors("https://example.com/page")

    assert result["selectors"] == LLM_RESPONSE["selectors"]
    assert result["domain"] == "example.com"
    assert result["description"] == LLM_RESPONSE["description"]
    assert "samples" in result
    assert result["samples"]["title"] == ["Test Title"]


@pytest.mark.asyncio
async def test_auto_discover_caches_result_by_domain():
    """Result is stored in Redis after first call."""
    redis = FakeRedis()

    with patch("app.auto_discover._fetch_html", return_value=SAMPLE_HTML), \
         patch("app.auto_discover._call_groq", return_value=LLM_RESPONSE):
        await auto_discover_selectors("https://example.com/page", redis=redis)

    cached = await redis.get("auto_discover:domain:example.com")
    assert cached is not None
    cached_data = json.loads(cached)
    assert cached_data["selectors"] == LLM_RESPONSE["selectors"]


@pytest.mark.asyncio
async def test_auto_discover_cache_hit_skips_fetch_and_llm():
    """Second call for same domain uses cache; fetch + LLM are NOT called."""
    redis = FakeRedis()

    # Populate cache manually
    cached_result = {
        "url": "https://example.com/page",
        "domain": "example.com",
        "selectors": {"title": "h1"},
        "description": "cached",
        "samples": {"title": ["Cached Title"]},
    }
    await redis.setex(
        "auto_discover:domain:example.com",
        3600,
        json.dumps(cached_result),
    )

    with patch("app.auto_discover._fetch_html") as mock_fetch, \
         patch("app.auto_discover._call_groq") as mock_groq:
        result = await auto_discover_selectors(
            "https://example.com/other-page", redis=redis
        )
        mock_fetch.assert_not_called()
        mock_groq.assert_not_called()

    assert result["selectors"] == {"title": "h1"}
    assert result["description"] == "cached"


@pytest.mark.asyncio
async def test_auto_discover_no_redis():
    """Works without Redis — no caching, returns result normally."""
    with patch("app.auto_discover._fetch_html", return_value=SAMPLE_HTML), \
         patch("app.auto_discover._call_groq", return_value=LLM_RESPONSE):
        result = await auto_discover_selectors("https://example.com/page", redis=None)

    assert result["selectors"] == LLM_RESPONSE["selectors"]


@pytest.mark.asyncio
async def test_auto_discover_endpoint(async_client):
    """POST /api/jobs/auto-discover returns selectors + samples."""
    with patch("app.auto_discover._fetch_html", return_value=SAMPLE_HTML), \
         patch("app.auto_discover._call_groq", return_value=LLM_RESPONSE), \
         patch("app.api.routes.aioredis") if False else patch(
             "redis.asyncio.from_url", side_effect=Exception("no redis")
         ):
        # Patch auto_discover_selectors directly to avoid Redis setup in endpoint
        with patch(
            "app.api.routes.auto_discover_selectors" if False else
            "app.auto_discover.auto_discover_selectors",
        ) as mock_discover:
            mock_discover.return_value = {
                "url": "https://example.com/page",
                "domain": "example.com",
                "selectors": LLM_RESPONSE["selectors"],
                "description": LLM_RESPONSE["description"],
                "samples": {"title": ["Test Title"]},
            }
            response = await async_client.post(
                "/api/jobs/auto-discover",
                json={"url": "https://example.com/page"},
            )

    assert response.status_code == 200
    data = response.json()
    assert "selectors" in data
    assert "samples" in data
    assert data["domain"] == "example.com"

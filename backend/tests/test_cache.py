"""Tests for the Redis caching layer (T-002)."""
import json
import pytest
import pytest_asyncio
import fakeredis.aioredis

from app.cache import (
    _make_cache_key,
    get_cached_result,
    set_cached_result,
    DEFAULT_TTL,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def redis():
    """Fake async Redis instance for each test."""
    client = fakeredis.aioredis.FakeRedis()
    yield client
    await client.flushall()
    await client.aclose()


# ---------------------------------------------------------------------------
# _make_cache_key tests
# ---------------------------------------------------------------------------

def test_cache_key_is_deterministic():
    """Same url + selectors always produce the same key."""
    key1 = _make_cache_key("https://example.com", {"title": "h1"})
    key2 = _make_cache_key("https://example.com", {"title": "h1"})
    assert key1 == key2


def test_cache_key_differs_for_different_selectors():
    """Different selectors produce a different key."""
    key1 = _make_cache_key("https://example.com", {"title": "h1"})
    key2 = _make_cache_key("https://example.com", {"title": "h2"})
    assert key1 != key2


def test_cache_key_differs_for_different_urls():
    """Different URLs produce a different key."""
    key1 = _make_cache_key("https://example.com", {"title": "h1"})
    key2 = _make_cache_key("https://other.com", {"title": "h1"})
    assert key1 != key2


def test_cache_key_has_prefix():
    """Cache keys start with the expected namespace prefix."""
    key = _make_cache_key("https://example.com", {"title": "h1"})
    assert key.startswith("scraper:cache:")


# ---------------------------------------------------------------------------
# Cache miss tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cache_miss_returns_none(redis):
    """get_cached_result returns None when the key is absent."""
    result = await get_cached_result(redis, "https://example.com", {"title": "h1"})
    assert result is None


@pytest.mark.asyncio
async def test_cache_miss_with_none_redis():
    """get_cached_result returns None gracefully when redis is None."""
    result = await get_cached_result(None, "https://example.com", {"title": "h1"})
    assert result is None


# ---------------------------------------------------------------------------
# Cache hit tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cache_hit_returns_data(redis):
    """After storing, get_cached_result returns the exact data."""
    data = [{"title": "Hello"}, {"title": "World"}]
    await set_cached_result(redis, "https://example.com", {"title": "h1"}, data)
    result = await get_cached_result(redis, "https://example.com", {"title": "h1"})
    assert result == data


@pytest.mark.asyncio
async def test_cache_hit_empty_list(redis):
    """An empty result list is cached and returned correctly."""
    await set_cached_result(redis, "https://example.com", {"title": "h1"}, [])
    result = await get_cached_result(redis, "https://example.com", {"title": "h1"})
    assert result == []


# ---------------------------------------------------------------------------
# TTL / expiry tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_set_cached_result_uses_ttl(redis):
    """set_cached_result stores the key with the given TTL."""
    data = [{"title": "Test"}]
    await set_cached_result(redis, "https://example.com", {"title": "h1"}, data, ttl=60)
    key = _make_cache_key("https://example.com", {"title": "h1"})
    ttl_remaining = await redis.ttl(key)
    assert 0 < ttl_remaining <= 60


@pytest.mark.asyncio
async def test_default_ttl_is_300(redis):
    """set_cached_result defaults to a 300-second TTL."""
    data = [{"title": "Test"}]
    await set_cached_result(redis, "https://example.com", {"title": "h1"}, data)
    key = _make_cache_key("https://example.com", {"title": "h1"})
    ttl_remaining = await redis.ttl(key)
    assert 0 < ttl_remaining <= DEFAULT_TTL


# ---------------------------------------------------------------------------
# Graceful degradation tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_set_cached_result_noop_with_none_redis():
    """set_cached_result is a no-op when redis is None."""
    # Should not raise
    await set_cached_result(None, "https://example.com", {"title": "h1"}, [{"x": 1}])


@pytest.mark.asyncio
async def test_different_selectors_have_independent_cache(redis):
    """Results for different selectors are stored independently."""
    data_a = [{"title": "A"}]
    data_b = [{"price": "99"}]

    await set_cached_result(redis, "https://example.com", {"title": "h1"}, data_a)
    await set_cached_result(redis, "https://example.com", {"price": ".price"}, data_b)

    result_a = await get_cached_result(redis, "https://example.com", {"title": "h1"})
    result_b = await get_cached_result(redis, "https://example.com", {"price": ".price"})

    assert result_a == data_a
    assert result_b == data_b

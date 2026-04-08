import hashlib
import json
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)

DEFAULT_TTL = 300  # seconds


def _make_cache_key(url: str, selectors: dict) -> str:
    """Generate a deterministic cache key from URL and selectors."""
    payload = json.dumps({"url": url, "selectors": selectors}, sort_keys=True)
    digest = hashlib.sha256(payload.encode()).hexdigest()
    return f"scraper:cache:{digest}"


async def get_cached_result(
    redis,
    url: str,
    selectors: dict,
) -> Optional[List[dict]]:
    """
    Return cached scraping results for the given URL + selectors, or None on miss/error.
    Gracefully degrades if redis is None or unavailable.
    """
    if redis is None:
        return None
    try:
        key = _make_cache_key(url, selectors)
        data = await redis.get(key)
        if data is None:
            return None
        return json.loads(data)
    except Exception as exc:
        logger.warning(f"Cache get error: {exc}")
        return None


async def set_cached_result(
    redis,
    url: str,
    selectors: dict,
    results: List[dict],
    ttl: int = DEFAULT_TTL,
) -> None:
    """
    Store scraping results in cache with a configurable TTL (default 300s).
    Gracefully degrades if redis is None or unavailable.
    """
    if redis is None:
        return
    try:
        key = _make_cache_key(url, selectors)
        await redis.setex(key, ttl, json.dumps(results))
    except Exception as exc:
        logger.warning(f"Cache set error: {exc}")

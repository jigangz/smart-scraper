"""LLM-powered CSS selector auto-discovery using Groq API."""
from __future__ import annotations

import json
import logging
import os
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

CACHE_KEY_PREFIX = "auto_discover:domain:"
CACHE_TTL = 3600  # 1 hour

_GROQ_SYSTEM_PROMPT = (
    "You are a web scraping expert. Given HTML content, identify the best CSS selectors "
    "to extract structured data. Return a JSON object with this exact structure:\n"
    '{"selectors": {"field_name": "css_selector", ...}, "description": "brief description"}\n'
    "Focus on the main content (articles, products, listings, etc.). "
    "Use specific, reliable selectors. Return valid JSON only."
)


def _get_domain(url: str) -> str:
    """Extract the netloc (domain) from a URL."""
    return urlparse(url).netloc


def _truncate_html(html: str, max_chars: int = 32000) -> str:
    """Truncate HTML to approximately 8K tokens (~32K chars)."""
    if len(html) <= max_chars:
        return html
    return html[:max_chars]


async def _fetch_html(url: str) -> str:
    """Fetch page HTML via httpx."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; SmartScraper/1.0)"}
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.text


def _call_groq(html: str) -> dict:
    """Call Groq API (Llama 3.3) to generate CSS selector suggestions."""
    from groq import Groq  # imported lazily so tests can mock without installing

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set")

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": _GROQ_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Analyze this HTML and suggest CSS selectors:\n\n{html}",
            },
        ],
        response_format={"type": "json_object"},
        max_tokens=1024,
    )
    content = response.choices[0].message.content
    return json.loads(content)


def _sample_extract(html: str, selectors: dict) -> dict:
    """Use BeautifulSoup to sample-extract data with the given selectors."""
    soup = BeautifulSoup(html, "html.parser")
    samples: dict = {}
    for field, selector in selectors.items():
        try:
            elements = soup.select(selector)[:3]
            samples[field] = [el.get_text(strip=True) for el in elements]
        except Exception:
            samples[field] = []
    return samples


async def auto_discover_selectors(url: str, redis=None) -> dict:
    """
    Discover CSS selectors for a URL using the Groq LLM.

    Steps:
      1. Check Redis cache by domain (return cached result if found).
      2. Fetch page HTML.
      3. Truncate to ~8K tokens.
      4. Call Groq API to generate selectors.
      5. Sample-extract data from the page using returned selectors.
      6. Cache the result by domain in Redis.
      7. Return selectors + samples.
    """
    domain = _get_domain(url)
    cache_key = f"{CACHE_KEY_PREFIX}{domain}"

    # --- Cache lookup ---
    if redis is not None:
        try:
            cached = await redis.get(cache_key)
            if cached:
                logger.debug("auto_discover cache hit for domain=%s", domain)
                return json.loads(cached)
        except Exception as exc:
            logger.warning("Redis cache get failed: %s", exc)

    # --- Fetch + LLM ---
    html = await _fetch_html(url)
    truncated = _truncate_html(html)
    llm_result = _call_groq(truncated)

    selectors = llm_result.get("selectors", {})
    description = llm_result.get("description", "")

    # --- Sample extraction ---
    samples = _sample_extract(html, selectors)

    result = {
        "url": url,
        "domain": domain,
        "selectors": selectors,
        "description": description,
        "samples": samples,
    }

    # --- Cache by domain if we got selectors ---
    if selectors and redis is not None:
        try:
            await redis.setex(cache_key, CACHE_TTL, json.dumps(result))
        except Exception as exc:
            logger.warning("Redis cache set failed: %s", exc)

    return result

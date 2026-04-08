import logging
import time
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Job, Result, Log
from app.scraper.anti_detect import AntiDetection
from app.scraper.parsers import parse_html, extract_pagination_url
from app.cache import get_cached_result, set_cached_result

logger = logging.getLogger(__name__)

# Scrapling fetcher modes
MODES = ("fast", "dynamic", "stealth")
FALLBACK_ORDER = {"fast": "dynamic", "dynamic": "stealth", "stealth": None}


def _scrapling_fetch(
    url: str,
    mode: str,
    proxy: Optional[str] = None,
    cookies: Optional[List[dict]] = None,
):
    """
    Synchronous Scrapling fetch using the specified mode.
    Returns a Scrapling page/response object.
    Cookies are injected as a name→value dict for fast mode and as a list of
    dicts for browser-based modes (dynamic/stealth).
    """
    from scrapling.fetchers import Fetcher, StealthyFetcher, DynamicFetcher

    common_kwargs = {}
    if proxy:
        common_kwargs["proxy"] = proxy

    if mode == "fast":
        if cookies:
            common_kwargs["cookies"] = {c["name"]: c["value"] for c in cookies}
        return Fetcher.get(url, **common_kwargs)

    elif mode == "dynamic":
        if cookies:
            common_kwargs["cookies"] = cookies
        return DynamicFetcher.fetch(
            url,
            headless=True,
            network_idle=True,
            **common_kwargs,
        )

    elif mode == "stealth":
        if cookies:
            common_kwargs["cookies"] = cookies
        return StealthyFetcher.fetch(
            url,
            headless=True,
            network_idle=True,
            **common_kwargs,
        )

    raise ValueError(f"Unknown scraping mode: {mode}")


def _extract_with_scrapling(page, selectors: dict) -> list[dict]:
    """
    Use Scrapling's CSS selector engine with adaptive element tracking.
    Falls back to the legacy BeautifulSoup parser if Scrapling returns nothing.
    """
    # Determine the "container" selector if provided, otherwise use the first selector
    # to discover how many items exist on the page.
    selector_items = list(selectors.items())
    if not selector_items:
        return []

    # Try to detect a repeated element by checking the first selector
    first_key, first_sel = selector_items[0]
    # Strip optional @attribute suffix for the CSS query
    css_sel = first_sel.split("@")[0].strip() if "@" in first_sel else first_sel

    try:
        anchors = page.css(css_sel, auto_save=True)
    except Exception:
        anchors = page.css(css_sel)

    if not anchors:
        return []

    count = len(anchors)
    results: list[dict] = []

    for i in range(count):
        row: dict = {}
        for key, sel in selector_items:
            attr = None
            if "@" in sel:
                sel_part, attr = sel.rsplit("@", 1)
                sel_part = sel_part.strip()
            else:
                sel_part = sel
                attr = None

            try:
                elements = page.css(sel_part, auto_save=True)
            except Exception:
                elements = page.css(sel_part)

            if elements and i < len(elements):
                el = elements[i]
                if attr:
                    row[key] = el.attrib.get(attr, "")
                else:
                    row[key] = el.text.strip() if el.text else ""
            else:
                row[key] = ""
        results.append(row)

    return results


def _execute_interactions(page, interactions: List[dict]) -> None:
    """
    Execute a sequence of interaction steps on a scraped page object.

    Supports: click, scroll, wait (for selector), type, select.
    Only called for dynamic and stealth modes; fast mode ignores interactions.

    ``page`` must expose an ``execute_js(script: str)`` method.
    """
    for step in interactions:
        action = step.get("action", "")
        selector = step.get("selector") or ""
        value = step.get("value") or ""
        repeat = int(step.get("repeat") or 1)
        wait_ms = int(step.get("wait_ms") or 0)

        for _ in range(repeat):
            if action == "click" and selector:
                sel = selector.replace("'", "\\'")
                page.execute_js(f"document.querySelector('{sel}')?.click();")
            elif action == "scroll":
                page.execute_js("window.scrollTo(0, document.body.scrollHeight);")
            elif action == "wait" and selector:
                sel = selector.replace("'", "\\'")
                page.execute_js(
                    f"(function() {{"
                    f"  var el = document.querySelector('{sel}');"
                    f"  return el !== null;"
                    f"}})();"
                )
            elif action == "type" and selector:
                sel = selector.replace("'", "\\'")
                val = value.replace("'", "\\'")
                page.execute_js(
                    f"var el = document.querySelector('{sel}');"
                    f"if (el) {{ el.value = '{val}'; }}"
                )
            elif action == "select" and selector:
                sel = selector.replace("'", "\\'")
                val = value.replace("'", "\\'")
                page.execute_js(
                    f"var el = document.querySelector('{sel}');"
                    f"if (el) {{ el.value = '{val}'; }}"
                )

            if wait_ms > 0:
                time.sleep(wait_ms / 1000.0)


class ScrapingEngine:
    def __init__(self, job_id: int, db_session: AsyncSession, redis=None, cache_ttl: int = 300):
        self.job_id = job_id
        self.db_session = db_session
        self.redis = redis
        self.cache_ttl = cache_ttl

    def _execute_interactions(self, page, interactions: List[dict]) -> None:
        """Delegate to module-level _execute_interactions (testable via instance method)."""
        _execute_interactions(page, interactions)

    async def scrape_with_mode(
        self,
        url: str,
        selectors: dict,
        mode: str,
        anti_detection: AntiDetection,
        interactions: Optional[List[dict]] = None,
        cookies: Optional[List[dict]] = None,
    ) -> list[dict]:
        """
        Scrape a URL using a Scrapling fetcher mode.
        Uses the legacy AntiDetection layer for proxy and extra checks.
        """
        await self._log(
            self.job_id, "info",
            f"Scrapling {mode} mode scrape: {url}",
        )

        proxy = anti_detection.get_proxy()

        try:
            import asyncio
            import functools
            loop = asyncio.get_event_loop()
            page = await loop.run_in_executor(
                None,
                functools.partial(_scrapling_fetch, url, mode, proxy, cookies),
            )
        except Exception as e:
            await self._log(
                self.job_id, "error",
                f"Scrapling {mode} fetch failed for {url}: {e}",
            )
            return []

        # Execute interactions after page load (dynamic/stealth only)
        if mode != "fast" and interactions:
            try:
                await loop.run_in_executor(
                    None, self._execute_interactions, page, interactions
                )
            except Exception as e:
                await self._log(
                    self.job_id, "warning",
                    f"Interactions failed for {url} ({mode} mode): {e}",
                )

        # Try Scrapling's own CSS engine first
        results = _extract_with_scrapling(page, selectors)

        # Fallback: use legacy BeautifulSoup parser on the raw HTML
        if not results:
            try:
                html = str(page.html_content) if hasattr(page, "html_content") else str(page)
                if anti_detection.detect_captcha(html):
                    await self._log(
                        self.job_id, "warning",
                        f"CAPTCHA detected at {url} ({mode} mode)",
                    )
                    return []
                results = parse_html(html, selectors)
            except Exception:
                pass

        await self._log(
            self.job_id, "info",
            f"Scrapling {mode} mode found {len(results)} items from {url}",
        )
        return results

    async def run(self, job: Job) -> dict:
        """
        Main entry point.
        Uses Scrapling fetchers with auto-fallback: fast → dynamic → stealth.
        Handles pagination. Saves results to DB.
        """
        await self._log(self.job_id, "info", f"Starting job '{job.name}' for {job.url}")

        # Check cache before scraping
        cached = await get_cached_result(self.redis, job.url, job.selectors)
        if cached is not None:
            await self._log(
                self.job_id, "info",
                f"Cache hit for {job.url} — returning {len(cached)} cached results",
            )
            if cached:
                await self._save_results(self.job_id, cached)
            return {
                "status": "completed",
                "results_count": len(cached),
                "pages_scraped": 0,
                "cache_hit": True,
            }

        mode = getattr(job, "mode", None) or "fast"
        if mode not in MODES:
            mode = "fast"

        # Extract interactions (only applied for dynamic/stealth modes)
        job_interactions = getattr(job, "interactions", None)
        interactions: Optional[List[dict]] = (
            job_interactions if isinstance(job_interactions, list) else None
        )

        # Decrypt and extract cookies for injection
        raw_cookies = getattr(job, "cookies", None)
        if raw_cookies and isinstance(raw_cookies, list):
            from app.cookie_encryption import decrypt_cookies
            job_cookies: Optional[List[dict]] = decrypt_cookies(raw_cookies)
        else:
            job_cookies = None

        # Configure anti-detection layer
        if job.anti_detection:
            anti_detection_config = {
                "min_delay": 2.0,
                "max_delay": 5.0,
                "max_retries": 3,
            }
        else:
            anti_detection_config = {
                "min_delay": 0.1,
                "max_delay": 0.5,
                "max_retries": 1,
            }

        anti = AntiDetection(anti_detection_config)
        all_results = []
        current_url: Optional[str] = job.url
        page_num = 0
        max_pages = 10

        if job.pagination_config and isinstance(job.pagination_config, dict):
            max_pages = job.pagination_config.get("max_pages", 10)

        try:
            while current_url and page_num < max_pages:
                page_num += 1
                await self._log(
                    self.job_id, "info",
                    f"Scraping page {page_num}: {current_url}",
                )

                # Scrape with current mode
                results = await self.scrape_with_mode(
                    current_url, job.selectors, mode, anti, interactions, job_cookies
                )

                # Auto-fallback: try next mode if no results
                current_mode = mode
                while not results and FALLBACK_ORDER.get(current_mode):
                    next_mode = FALLBACK_ORDER[current_mode]
                    await self._log(
                        self.job_id, "info",
                        f"{current_mode} mode returned no results, "
                        f"falling back to {next_mode}...",
                    )
                    results = await self.scrape_with_mode(
                        current_url, job.selectors, next_mode, anti, interactions, job_cookies
                    )
                    current_mode = next_mode

                all_results.extend(results)

                # Check for next page
                if job.pagination_config and results:
                    try:
                        pagination_config = dict(job.pagination_config)
                        pagination_config["current_page"] = page_num
                        pagination_config["max_pages"] = max_pages

                        response = await anti.request_with_retry(current_url)
                        current_url = extract_pagination_url(
                            response.text, pagination_config, current_url
                        )
                    except Exception as e:
                        await self._log(
                            self.job_id, "warning",
                            f"Pagination error: {str(e)}",
                        )
                        current_url = None
                else:
                    current_url = None

            # Save results
            if all_results:
                await self._save_results(self.job_id, all_results)

            # Cache the results for future requests
            await set_cached_result(
                self.redis, job.url, job.selectors, all_results, ttl=self.cache_ttl
            )

            summary = {
                "status": "completed",
                "results_count": len(all_results),
                "pages_scraped": page_num,
            }

            await self._log(
                self.job_id, "info",
                f"Job completed: {len(all_results)} results from {page_num} page(s)",
            )
            return summary

        except Exception as e:
            error_msg = f"Job failed: {str(e)}"
            await self._log(self.job_id, "error", error_msg)
            return {
                "status": "failed",
                "results_count": len(all_results),
                "error": str(e),
            }

    async def _save_results(self, job_id: int, results: list[dict]):
        """Save scraped results to the Results table."""
        for data in results:
            result = Result(
                job_id=job_id,
                data=data,
                scraped_at=datetime.now(timezone.utc),
            )
            self.db_session.add(result)
        await self.db_session.commit()

    async def _log(self, job_id: int, level: str, message: str):
        """Save a log entry to the Logs table."""
        logger.log(
            getattr(logging, level.upper(), logging.INFO),
            f"[Job {job_id}] {message}",
        )
        log_entry = Log(
            job_id=job_id,
            level=level,
            message=message,
            timestamp=datetime.now(timezone.utc),
        )
        self.db_session.add(log_entry)
        try:
            await self.db_session.commit()
        except Exception:
            await self.db_session.rollback()

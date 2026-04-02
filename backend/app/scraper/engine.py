import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Job, Result, Log
from app.scraper.anti_detect import AntiDetection
from app.scraper.parsers import parse_html, extract_pagination_url

logger = logging.getLogger(__name__)

# Scrapling fetcher modes
MODES = ("fast", "dynamic", "stealth")
FALLBACK_ORDER = {"fast": "dynamic", "dynamic": "stealth", "stealth": None}


def _scrapling_fetch(url: str, mode: str, proxy: Optional[str] = None):
    """
    Synchronous Scrapling fetch using the specified mode.
    Returns a Scrapling page/response object.
    """
    from scrapling.fetchers import Fetcher, StealthyFetcher, PlayWrightFetcher

    common_kwargs = {}
    if proxy:
        common_kwargs["proxy"] = proxy

    if mode == "fast":
        return Fetcher.get(url, **common_kwargs)

    elif mode == "dynamic":
        return PlayWrightFetcher.fetch(
            url,
            headless=True,
            network_idle=True,
            **common_kwargs,
        )

    elif mode == "stealth":
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


class ScrapingEngine:
    def __init__(self, job_id: int, db_session: AsyncSession):
        self.job_id = job_id
        self.db_session = db_session

    async def scrape_with_mode(
        self,
        url: str,
        selectors: dict,
        mode: str,
        anti_detection: AntiDetection,
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
            loop = asyncio.get_event_loop()
            page = await loop.run_in_executor(
                None, _scrapling_fetch, url, mode, proxy
            )
        except Exception as e:
            await self._log(
                self.job_id, "error",
                f"Scrapling {mode} fetch failed for {url}: {e}",
            )
            return []

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

        mode = getattr(job, "mode", None) or "fast"
        if mode not in MODES:
            mode = "fast"

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
                    current_url, job.selectors, mode, anti
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
                        current_url, job.selectors, next_mode, anti
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

import asyncio
import random
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

USER_AGENTS = [
    # Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Chrome on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Chrome on Linux
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    # Firefox on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:118.0) Gecko/20100101 Firefox/118.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:117.0) Gecko/20100101 Firefox/117.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    # Firefox on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0",
    # Firefox on Linux
    "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:119.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (X11; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    # Safari on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    # Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36 Edg/118.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
    # Edge on Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.0.0",
    # Chrome on Windows 11
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 OPR/106.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 OPR/105.0.0.0",
    # Additional Chrome variants
    "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Vivaldi/6.5.3206.50",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Brave/1.61",
]

ACCEPT_LANGUAGES = [
    "en-US,en;q=0.9",
    "en-US,en;q=0.9,es;q=0.8",
    "en-GB,en;q=0.9,en-US;q=0.8",
    "en-US,en;q=0.9,fr;q=0.8",
    "en-US,en;q=0.9,de;q=0.8",
    "en-US,en;q=0.9,ja;q=0.8",
    "en-US,en;q=0.9,zh-CN;q=0.8",
    "en-US,en;q=0.9,pt-BR;q=0.8",
    "en-US,en;q=0.9,ko;q=0.8",
    "en-US,en;q=0.9,it;q=0.8",
    "en-GB,en;q=0.9",
    "en-CA,en;q=0.9,fr;q=0.8",
    "en-AU,en;q=0.9",
    "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
]

REFERERS = [
    "https://www.google.com/",
    "https://www.google.com/search?q=",
    "https://www.bing.com/",
    "https://www.bing.com/search?q=",
    "https://search.yahoo.com/",
    "https://duckduckgo.com/",
    "https://www.baidu.com/",
    "https://yandex.com/",
    None,  # direct visit
    None,
]

TIMEZONES = [
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "Europe/London",
    "Europe/Berlin",
    "Europe/Paris",
    "Asia/Tokyo",
    "Asia/Shanghai",
    "Australia/Sydney",
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
    {"width": 1280, "height": 720},
    {"width": 1600, "height": 900},
    {"width": 2560, "height": 1440},
    {"width": 1280, "height": 800},
    {"width": 1680, "height": 1050},
    {"width": 1360, "height": 768},
]

CAPTCHA_INDICATORS = [
    "g-recaptcha",
    "recaptcha",
    "h-captcha",
    "hcaptcha",
    "cf-challenge",
    "challenge-platform",
    "cf-turnstile",
    "captcha-delivery",
    "px-captcha",
    "arkose",
    "funcaptcha",
    "challenge-form",
    "captcha",
    "please verify you are a human",
    "verify you are human",
    "bot detection",
    "access denied",
    "just a moment",
    "checking your browser",
    "ray id",
]


class AntiDetection:
    def __init__(self, config: Optional[dict] = None):
        config = config or {}
        self.proxy_url: Optional[str] = config.get("proxy_url")
        self.min_delay: float = config.get("min_delay", 2.0)
        self.max_delay: float = config.get("max_delay", 5.0)
        self.max_retries: int = config.get("max_retries", 3)

    def get_headers(self) -> dict:
        ua = random.choice(USER_AGENTS)
        referer = random.choice(REFERERS)

        headers = {
            "User-Agent": ua,
            "Accept": random.choice([
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            ]),
            "Accept-Language": random.choice(ACCEPT_LANGUAGES),
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": random.choice(["keep-alive", "Keep-Alive"]),
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": random.choice(["document", "empty"]),
            "Sec-Fetch-Mode": random.choice(["navigate", "cors", "no-cors"]),
            "Sec-Fetch-Site": random.choice(["none", "same-origin", "cross-site"]),
            "Sec-Fetch-User": "?1",
            "Cache-Control": random.choice(["max-age=0", "no-cache"]),
        }

        if referer:
            headers["Referer"] = referer

        # Randomly add or omit optional headers
        if random.random() > 0.5:
            headers["DNT"] = "1"

        if random.random() > 0.7:
            headers["Sec-CH-UA-Platform"] = random.choice([
                '"Windows"', '"macOS"', '"Linux"'
            ])

        return headers

    def get_random_delay(self) -> float:
        return random.uniform(self.min_delay, self.max_delay)

    async def wait(self):
        delay = self.get_random_delay()
        logger.debug(f"Anti-detection delay: {delay:.2f}s")
        await asyncio.sleep(delay)

    def get_proxy(self) -> Optional[dict]:
        if not self.proxy_url:
            return None
        return {
            "http://": self.proxy_url,
            "https://": self.proxy_url,
        }

    def detect_captcha(self, html: str) -> bool:
        html_lower = html.lower()
        for indicator in CAPTCHA_INDICATORS:
            if indicator.lower() in html_lower:
                logger.warning(f"CAPTCHA detected: found '{indicator}' in response")
                return True
        return False

    def get_playwright_context_options(self) -> dict:
        viewport = random.choice(VIEWPORTS)
        ua = random.choice(USER_AGENTS)
        timezone = random.choice(TIMEZONES)
        locale = random.choice([
            "en-US", "en-GB", "en-CA", "en-AU", "de-DE", "fr-FR"
        ])
        color_scheme = random.choice(["light", "dark", "no-preference"])

        return {
            "viewport": viewport,
            "user_agent": ua,
            "locale": locale,
            "timezone_id": timezone,
            "color_scheme": color_scheme,
            "java_script_enabled": True,
            "has_touch": random.choice([True, False]),
            "is_mobile": False,
            "device_scale_factor": random.choice([1, 1.25, 1.5, 2]),
        }

    async def request_with_retry(
        self,
        url: str,
        session: Optional[httpx.AsyncClient] = None,
        max_retries: Optional[int] = None,
    ) -> httpx.Response:
        retries = max_retries if max_retries is not None else self.max_retries
        last_exception = None
        own_session = session is None

        if own_session:
            proxy = self.proxy_url
            session = httpx.AsyncClient(
                proxy=proxy,
                follow_redirects=True,
                timeout=30.0,
            )

        try:
            for attempt in range(retries):
                try:
                    headers = self.get_headers()

                    if attempt > 0:
                        backoff = min(2 ** attempt + random.uniform(0, 1), 30)
                        logger.info(
                            f"Retry {attempt}/{retries} for {url}, "
                            f"backoff: {backoff:.2f}s"
                        )
                        await asyncio.sleep(backoff)
                    else:
                        await self.wait()

                    response = await session.get(url, headers=headers)
                    response.raise_for_status()

                    if self.detect_captcha(response.text):
                        logger.warning(
                            f"CAPTCHA detected on attempt {attempt + 1} for {url}"
                        )
                        if attempt < retries - 1:
                            continue
                        raise Exception(
                            f"CAPTCHA detected after {retries} attempts for {url}"
                        )

                    return response

                except httpx.HTTPStatusError as e:
                    last_exception = e
                    logger.warning(
                        f"HTTP {e.response.status_code} on attempt "
                        f"{attempt + 1} for {url}"
                    )
                    if e.response.status_code in (403, 429, 503):
                        continue
                    raise
                except httpx.RequestError as e:
                    last_exception = e
                    logger.warning(
                        f"Request error on attempt {attempt + 1} for {url}: {e}"
                    )
                    continue

            raise Exception(
                f"Max retries ({retries}) exceeded for {url}: {last_exception}"
            )
        finally:
            if own_session:
                await session.aclose()

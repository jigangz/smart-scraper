from prometheus_client import Counter, Histogram, Gauge

scraper_requests_total = Counter(
    "scraper_requests_total",
    "Total scraping requests by domain, mode, and status",
    ["domain", "mode", "status"],
)

scraper_request_duration_seconds = Histogram(
    "scraper_request_duration_seconds",
    "Scraping request duration in seconds",
    ["mode"],
)

scraper_cache_hits_total = Counter(
    "scraper_cache_hits_total",
    "Total cache hits",
)

scraper_cache_misses_total = Counter(
    "scraper_cache_misses_total",
    "Total cache misses",
)

scraper_queue_depth = Gauge(
    "scraper_queue_depth",
    "Current number of pending tasks in the scraping queue",
)

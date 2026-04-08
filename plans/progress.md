# Ralph Progress Log

Started: 2026-04-07
Project: smart-scraper infra upgrade (Celery + Redis + Monitoring + Features)

## Codebase Patterns

- Backend: FastAPI (Python 3.11) + SQLAlchemy async + SQLite (aiosqlite)
- Frontend: Next.js + React + TypeScript + Tailwind (DO NOT MODIFY)
- Scraping: Scrapling library (3 modes: fast/dynamic/stealth + auto-fallback)
- Current scheduling: APScheduler in-memory (to be replaced by Celery Beat)
- Current job execution: FastAPI BackgroundTasks (to be replaced by Celery)
- DB models: Job, Result, Log in backend/app/db/models.py
- API routes: backend/app/api/routes.py (all endpoints under /api/)
- No existing tests

## Key Files

- `backend/app/main.py` — FastAPI app + lifespan (scheduler start/stop)
- `backend/app/api/routes.py` — All API endpoints + _run_job_task background function
- `backend/app/api/schemas.py` — Pydantic models (JobCreate, JobResponse, etc.)
- `backend/app/scraper/engine.py` — ScrapingEngine class (main scraping logic)
- `backend/app/scraper/scheduler.py` — APScheduler wrapper (to be replaced)
- `backend/app/scraper/anti_detect.py` — Anti-detection layer
- `backend/app/scraper/parsers.py` — HTML parsing + pagination
- `backend/app/db/models.py` — SQLAlchemy models (Job, Result, Log)
- `backend/app/db/database.py` — DB engine + session factory
- `docker-compose.yml` — backend + frontend services
- `backend/requirements.txt` — Python dependencies

## Important Notes

- Python 3.11 compatibility required (no 3.12+ syntax like `type X = ...`)
- Keep all existing API endpoints backward compatible
- Frontend is NOT in scope — do not modify any frontend files
- Use fakeredis for all Redis-dependent tests (no real Redis needed)
- Celery tasks must handle the case where Redis is unavailable gracefully

## Completed Tasks

### T-001: Celery + Redis async task queue (2026-04-07)

**Files created/modified:**
- `backend/app/worker.py` — Celery app + `run_scraping_task` with max_retries=3, exponential backoff (60/120/240s), uses `asyncio.run()` inside task (SIGN-012)
- `backend/app/api/routes.py` — Added `from app.worker import run_scraping_task, celery_app` at module level. Modified `POST /api/jobs/{id}/run` to submit Celery task and return `task_id` (falls back to BackgroundTasks on error). Added `GET /api/jobs/{id}/task-status` endpoint.
- `docker-compose.yml` — Added `redis` (port 6379) and `worker` services; backend/worker depend on redis health check
- `backend/tests/__init__.py` — Empty init
- `backend/tests/conftest.py` — `async_client` fixture uses `tmp_path` for isolated SQLite DB, patches `init_db` and scheduler; `test_job` fixture creates job via API
- `backend/tests/test_worker.py` — 10 tests (4 unit, 6 API)
- `backend/pytest.ini` — `asyncio_mode = auto`

**Key learnings:**
- f-strings with `dict["key"]` break on Python 3.11 — use a variable: `job_id = d["id"]`; then `f"/path/{job_id}"`
- Patch at the right location: `app.api.routes.run_scraping_task` (module-level import), NOT `app.worker.run_scraping_task`
- BackgroundTasks fallback test must also patch `_run_job_task` since it uses the global `async_session_factory` (not the test DB)
- `test_job` fixture creates job via API endpoint (depends on `async_client`) — simpler than managing session fixtures separately

---

### T-003: Replace APScheduler with Celery Beat (2026-04-07)

**Files created/modified:**
- `backend/requirements.txt` — Removed `apscheduler==3.10.4`, added `celery-redbeat` (pip package name for `redbeat`)
- `backend/app/scraper/scheduler.py` — Complete rewrite: `parse_schedule()` standalone function + `JobScheduler` using `RedBeatSchedulerEntry` for Redis-backed persistence. `start()`/`stop()` are now no-ops (Celery Beat runs as separate process)
- `backend/app/worker.py` — Added `beat_scheduler='redbeat.RedBeatScheduler'` and `redbeat_redis_url=REDIS_URL` to `celery_app.conf`
- `docker-compose.yml` — Added `beat` service running `celery beat --scheduler redbeat.RedBeatScheduler`
- `backend/tests/test_scheduler.py` — 14 tests: 8 for `parse_schedule`, 6 for `JobScheduler` (mocking redbeat)

**Key learnings:**
- The pip package name is `celery-redbeat` (not `redbeat`) — `import redbeat` still works after install
- `parse_schedule()` extracted as standalone function makes it easily unit-testable without any mocking
- `patch.dict('sys.modules', {'redbeat': mock_module})` lets `add_job`/`remove_job` tests work without a real Redis connection
- `JobScheduler.start()` and `stop()` remain as no-ops (API backward compatible with conftest.py patches)
- Celery Beat persistence via redbeat stores entries in Redis under `redbeat:{entry_name}` keys

---

### T-002: Redis caching layer (2026-04-07)

**Files created/modified:**
- `backend/app/cache.py` — `_make_cache_key` (sha256 of url+selectors JSON), `get_cached_result`, `set_cached_result` with TTL=300s default; graceful degradation when redis=None
- `backend/app/scraper/engine.py` — `ScrapingEngine.__init__` gains optional `redis` and `cache_ttl` params; `run()` checks cache before scraping, stores results after scraping
- `backend/tests/test_cache.py` — 12 tests: key determinism, miss, hit, empty list, TTL, different selectors isolation, None-redis noop

**Key learnings:**
- fakeredis.aioredis.FakeRedis supports `setex` and `ttl`, works identically to real Redis for cache tests
- ScrapingEngine receives redis as a constructor parameter (not global) — easy to mock in tests and backward-compatible (defaults to None)
- Cache hit returns early with `{"status": "completed", "cache_hit": True, ...}` without re-running scrape

---

### T-004: Prometheus metrics + health endpoint (2026-04-07)

**Files created/modified:**
- `backend/requirements.txt` — Added `prometheus-client==0.20.0`
- `backend/app/metrics.py` — Defines 5 metrics: `scraper_requests_total` (Counter, labels: domain/mode/status), `scraper_request_duration_seconds` (Histogram, label: mode), `scraper_cache_hits_total` (Counter), `scraper_cache_misses_total` (Counter), `scraper_queue_depth` (Gauge)
- `backend/app/api/routes.py` — Added `text` + `Response` imports; added `_check_redis()`, `_check_celery()`, `_check_db()` helper coroutines (patchable in tests); added `GET /metrics` (prometheus_client generate_latest) and `GET /health` endpoints
- `backend/tests/test_metrics.py` — 4 tests: 200 status, content-type, metric names present, repeatability
- `backend/tests/test_health.py` — 4 tests: all-healthy, redis-down→degraded, celery-down→degraded, db-down→unhealthy

**Key learnings:**
- prometheus_client's `generate_latest()` always emits `# HELP` and `# TYPE` lines for every registered metric, even before any observations — so tests can assert metric names are present without incrementing them
- Health sub-checks must be standalone async functions (not depending on `get_db`) so they can be patched with `AsyncMock` in tests
- Celery's `control.inspect().ping()` is synchronous — wrap in `run_in_executor` to avoid blocking the async event loop
- `import app.metrics` in the `/metrics` route handler ensures metrics are registered before `generate_latest()` is called

---

### T-005: Celery Flower + Prometheus + Grafana docker services (2026-04-07)

**Files created/modified:**
- `docker-compose.yml` — Added `flower` (port 5555), `prometheus` (port 9090), `grafana` (port 3001) services
- `monitoring/prometheus.yml` — Scrape config targeting `backend:8000` at `/metrics`
- `monitoring/grafana/provisioning/datasources/prometheus.yml` — Auto-provisions Prometheus datasource
- `monitoring/grafana/provisioning/dashboards/default.yml` — Auto-provisions dashboards from `/var/lib/grafana/dashboards`
- `monitoring/grafana/dashboards/scraper.json` — Pre-built dashboard with 6 panels: success rate, block rate, cache hit rate, queue depth, latency P50/P95, requests per second by mode

**Key learnings:**
- No tests needed for config files — this task is purely infrastructure/config
- Grafana uses `apiVersion: 1` in provisioning YAML files
- Grafana image exposes port 3000 internally — map to 3001 externally to avoid conflict with frontend
- All 44 existing tests still pass after this change

---

### T-006: Webhook + Redis Pub/Sub notifications (2026-04-07)

**Files created/modified:**
- `backend/app/notifications.py` — New module: `notify(job_id, message, webhook_url, redis)` publishes to `scraper:progress:{job_id}` Redis channel; `_post_webhook()` POSTs with 3 retries + exponential backoff via httpx
- `backend/app/db/models.py` — Added `webhook_url = Column(String, nullable=True)` to `Job`
- `backend/app/api/schemas.py` — Added `webhook_url: Optional[str] = None` to `JobCreate` and `JobResponse`
- `backend/app/api/routes.py` — Removed `_ws_connections` dict; `_notify_ws()` now publishes to Redis Pub/Sub via `notify()`; `create_job` passes `webhook_url`; WebSocket endpoint subscribes to `scraper:progress:{job_id}` with graceful Redis fallback
- `backend/app/worker.py` — Calls `notify()` after job completion (publishes to Redis + fires webhook)
- `backend/tests/test_notifications.py` — 8 tests: Redis publish, no-redis noop, Redis failure silence, webhook call, no webhook when None, POST success, retry exhaustion, retry success
- `backend/tests/test_webhook.py` — 6 tests: create with/without webhook_url, GET includes field, list includes field, run job flow, payload structure

**Key learnings:**
- `_ws_connections` in-process dict removed entirely; Redis Pub/Sub is now the sole broadcast mechanism
- WebSocket endpoint wraps Redis subscription in try/except — if Redis unavailable, WebSocket still works without real-time updates
- `asyncio.create_task(_listen_redis())` runs concurrently with WebSocket receive loop; cancelled on disconnect
- Worker imports `notify` inside `asyncio.run(_run())` — creates its own aioredis client and closes it after notify
- `_post_webhook` uses `httpx.AsyncClient` context manager; `asyncio.sleep` patching required for fast retry tests
- 58 tests pass after all changes

---

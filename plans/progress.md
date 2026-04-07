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

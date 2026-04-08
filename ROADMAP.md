# Smart Scraper Roadmap

## Completed — Infrastructure Upgrade (v2.0)

### [DONE] Celery + Redis Task Queue (T-001)
- Replaced FastAPI `BackgroundTasks` with Celery workers
- `max_retries=3` with exponential backoff (60/120/240s)
- `POST /api/jobs/{id}/run` returns Celery `task_id`
- `GET /api/jobs/{id}/task-status` returns task state + progress

### [DONE] Redis Caching Layer (T-002)
- Cache scrape results by SHA-256 hash of URL + selectors
- Configurable TTL (default 300s); graceful degradation when Redis unavailable

### [DONE] Celery Beat Scheduling (T-003)
- Replaced APScheduler with Celery Beat + redbeat
- Redis-backed persistent schedules (survive restarts)
- Supports cron expressions and interval strings (30m, 2h, 1d)

### [DONE] Prometheus Metrics + Health Endpoint (T-004)
- `GET /metrics` — scrape requests, latency, cache hits/misses, queue depth
- `GET /health` — Redis, Celery, and DB sub-checks with graceful degradation

### [DONE] Celery Flower + Prometheus + Grafana (T-005)
- Docker services for monitoring stack
- Pre-built Grafana dashboard: success rate, block rate, latency P50/P95, queue depth, cache hit rate

### [DONE] Webhook + Redis Pub/Sub Notifications (T-006)
- Optional `webhook_url` per job; POSTed on completion with 3 retries
- Redis Pub/Sub replaces in-memory WebSocket connections (multi-instance safe)

### [DONE] JS Interaction Support (T-007)
- `interactions` field in `JobCreate`: click, scroll, type, select, wait
- Runs after page load, before extraction (dynamic/stealth modes only)

### [DONE] Cookie/Session Injection (T-008)
- `cookies` field in `JobCreate`: inject browser cookies for authenticated scraping
- Fernet encryption at rest; `ENCRYPTION_KEY` env var; plaintext fallback with warning

### [DONE] LLM Auto-Selector (T-009)
- `POST /api/jobs/auto-discover`: fetch HTML → Groq Llama 3.3 → CSS selectors + samples
- Results cached by domain in Redis (1 hour TTL)
- Graceful fallback if `GROQ_API_KEY` not set

### [DONE] CI Update + Documentation (T-010)
- CI runs `pytest tests/ -v --tb=short` (replaced py_compile checks)
- README updated with architecture diagram, new features, docker-compose instructions
- ROADMAP updated with completed phases

---

## Planned — Phase 3: CAPTCHA Solving (Priority: Medium)

Integrate third-party CAPTCHA solving APIs for automated bypass.

**Implementation:**
- Add `captcha_config` to job config
- Support providers: 2Captcha, CapSolver, CapMonster
- Auto-detect CAPTCHA type (reCAPTCHA v2/v3, hCaptcha, Cloudflare Turnstile)
- Inject solution token and retry request

**Files to add:**
- `backend/app/scraper/captcha.py` — detection + solver integration

---

## Planned — Phase 5: Site Template Library (Priority: Low)

Pre-built selector templates for common sites (Indeed, LinkedIn, Glassdoor, HackerNews, RemoteOK).

**Storage:** `backend/templates/{site}.json` with selectors, mode, interactions, and anti-detection settings.

---

## Non-Goals

- Browser GUI for visual selector picking
- Distributed scraping cluster
- Built-in proxy pool management

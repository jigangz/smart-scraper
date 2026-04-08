# Smart Scraper

A production-ready web scraping platform with anti-detection, async task processing, and a dark-themed dashboard UI. Built with FastAPI, Celery, Redis, and Next.js.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Docker Compose                          │
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌────────────┐  │
│  │ frontend │   │ backend  │   │  worker  │   │    beat    │  │
│  │ Next.js  │──▶│ FastAPI  │──▶│  Celery  │   │Celery Beat │  │
│  │  :3000   │   │  :8000   │   │  worker  │   │ (redbeat)  │  │
│  └──────────┘   └────┬─────┘   └──────────┘   └────────────┘  │
│                      │              │                           │
│                 ┌────▼─────────────▼─────┐                     │
│                 │         Redis          │                      │
│                 │  cache / queue / pubsub│                      │
│                 └────────────────────────┘                      │
│                                                                 │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐                    │
│  │ flower   │   │prometheus│   │ grafana  │                    │
│  │  :5555   │   │  :9090   │   │  :3001   │                    │
│  └──────────┘   └──────────┘   └──────────┘                    │
└─────────────────────────────────────────────────────────────────┘
```

## Features

- **Scrapling-Powered Scraping Engine** — Three scraping modes:
  - **Fast Mode** — Pure HTTP via `Fetcher` (fastest, for static sites)
  - **Dynamic Mode** — Playwright-based via `DynamicFetcher` (for JS-rendered pages)
  - **Stealth Mode** — Max anti-detection via `StealthyFetcher` (bypasses Cloudflare, WAFs)
  - Auto-fallback: fast → dynamic → stealth if no results found
- **Celery + Redis Task Queue** — Async job execution with retries and exponential backoff
- **Celery Beat Scheduling** — Redis-backed persistent schedules (cron + interval strings)
- **Redis Caching** — Cache scrape results by URL + selectors (configurable TTL, default 5 min)
- **Prometheus Metrics** — `/metrics` endpoint with request counters, latency histograms, cache hit/miss, queue depth
- **Health Endpoint** — `/health` with Redis, Celery, and DB sub-checks
- **Grafana Dashboard** — Pre-built panels: success rate, block rate, latency P50/P95, queue depth, cache hit rate
- **JS Interactions** — Click, scroll, type, select, wait actions for dynamic pages
- **Cookie/Session Injection** — Inject browser cookies for authenticated scraping (stored encrypted with Fernet)
- **Webhook Notifications** — POST results to a webhook URL on job completion (3 retries)
- **Redis Pub/Sub WebSocket** — Real-time job progress via Redis channels (multi-instance safe)
- **LLM Auto-Selector** — `POST /api/jobs/auto-discover`: Groq Llama 3.3 generates CSS selectors from page HTML; results cached by domain
- **Advanced Anti-Detection** — TLS fingerprinting, CDP fix, WebRTC fix, canvas noise, headless bypass, 50+ User-Agents, proxy rotation
- **Data Export** — Export scraped data as CSV or JSON
- **Next.js Dashboard** — Dark-themed UI with real-time updates

## Quick Start

### Docker (Recommended)

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env: set GROQ_API_KEY, ENCRYPTION_KEY, etc.

# Start all services
docker-compose up --build
```

| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Celery Flower | http://localhost:5555 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 (admin/admin) |

### Manual Setup

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
python -m patchright install chromium

# Start Redis (required)
docker run -d -p 6379:6379 redis:7-alpine

# Start API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start Celery worker (separate terminal)
celery -A app.worker worker --loglevel=info

# Start Celery Beat scheduler (separate terminal)
celery -A app.worker beat --scheduler redbeat.RedBeatScheduler --loglevel=info
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection URL |
| `GROQ_API_KEY` | — | Groq API key for LLM auto-selector |
| `ENCRYPTION_KEY` | — | Fernet key for cookie encryption (generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./scraper.db` | Database URL |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/jobs` | Create a scraping job |
| `GET` | `/api/jobs` | List all jobs |
| `GET` | `/api/jobs/{id}` | Get job details + results |
| `POST` | `/api/jobs/{id}/run` | Run a job (returns Celery task_id) |
| `GET` | `/api/jobs/{id}/task-status` | Get Celery task state + progress |
| `DELETE` | `/api/jobs/{id}` | Delete a job |
| `POST` | `/api/jobs/auto-discover` | LLM-generate CSS selectors for a URL |
| `GET` | `/api/results/{job_id}` | Get scraped results |
| `GET` | `/api/results/{job_id}/export?format=csv` | Export as CSV |
| `GET` | `/api/results/{job_id}/export?format=json` | Export as JSON |
| `GET` | `/api/stats` | Dashboard statistics |
| `GET` | `/metrics` | Prometheus metrics |
| `GET` | `/health` | Health check (Redis, Celery, DB) |
| `WS` | `/ws/jobs/{id}` | Real-time job progress (Redis Pub/Sub) |

## Scraping Modes

| Mode | Fetcher | Best For | Speed |
|------|---------|----------|-------|
| **Fast** | `Fetcher` | Static HTML pages, APIs | Fastest |
| **Dynamic** | `DynamicFetcher` | JS-rendered SPAs, infinite scroll | Medium |
| **Stealth** | `StealthyFetcher` | Cloudflare, DataDome, bot-protected sites | Slowest |

## JS Interactions

Interactions execute after page load, before data extraction (dynamic/stealth modes only):

```json
{
  "interactions": [
    {"action": "scroll", "value": "bottom", "wait_ms": 2000},
    {"action": "click", "selector": "button.load-more", "repeat": 3, "wait_ms": 1500},
    {"action": "wait", "selector": ".results-loaded"},
    {"action": "type", "selector": "input#search", "value": "query"}
  ]
}
```

## Authenticated Scraping

```json
{
  "cookies": [
    {"name": "session", "value": "abc123", "domain": "example.com", "path": "/"}
  ]
}
```

Cookies are encrypted with Fernet before storage. Set `ENCRYPTION_KEY` env var.

## Project Structure

```
smart-scraper/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app entry
│   │   ├── worker.py             # Celery app + tasks
│   │   ├── cache.py              # Redis caching layer
│   │   ├── metrics.py            # Prometheus metrics
│   │   ├── notifications.py      # Webhooks + Redis Pub/Sub
│   │   ├── auto_discover.py      # LLM auto-selector (Groq)
│   │   ├── cookie_encryption.py  # Fernet cookie encryption
│   │   ├── api/
│   │   │   ├── routes.py         # All API endpoints
│   │   │   └── schemas.py        # Pydantic models
│   │   ├── scraper/
│   │   │   ├── engine.py         # Core scraping engine
│   │   │   ├── anti_detect.py    # Anti-detection system
│   │   │   ├── parsers.py        # HTML parsing
│   │   │   └── scheduler.py      # Celery Beat scheduler
│   │   └── db/
│   │       ├── database.py       # SQLite setup
│   │       └── models.py         # DB models (Job, Result, Log)
│   ├── tests/                    # pytest test suite (90+ tests)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                     # Next.js dashboard (do not modify)
├── monitoring/
│   ├── prometheus.yml            # Prometheus scrape config
│   └── grafana/                  # Grafana provisioning + dashboard
├── docker-compose.yml
└── README.md
```

## Tech Stack

### Backend
- **FastAPI** — Async Python web framework
- **Celery + Redis** — Distributed task queue with retry logic
- **Celery Beat + redbeat** — Redis-backed persistent job scheduling
- **SQLAlchemy** + **aiosqlite** — Async SQLite database
- **Scrapling** — Advanced anti-bot scraping framework
- **prometheus-client** — Metrics exposition
- **httpx** — Async HTTP client (scraping + webhooks)
- **Patchright** + **Playwright** — Anti-detection headless browsers
- **BeautifulSoup4** — HTML parsing
- **cryptography** — Fernet encryption for cookie storage
- **groq** — Groq API client for LLM auto-selector

### Frontend
- **Next.js 14** — React framework with App Router
- **shadcn/ui** — Radix UI + Tailwind CSS component library
- **Recharts** — Charting library
- **Framer Motion** — Animations
- **TypeScript** — Type safety

### Infrastructure
- **Redis 7** — Cache, task queue, Pub/Sub, Beat schedule store
- **Celery Flower** — Real-time task monitoring (port 5555)
- **Prometheus** — Metrics collection (port 9090)
- **Grafana** — Dashboard visualization (port 3001)

## Running Tests

```bash
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio fakeredis httpx
python -m pytest tests/ -v --tb=short
```

No external services required — Redis is mocked with `fakeredis`.

## License

MIT

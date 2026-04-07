# Smart Scraper

A production-ready web scraping platform with a beautiful dark-themed dashboard UI, built with FastAPI and Next.js.

## Features

- **Scrapling-Powered Scraping Engine** — Three scraping modes powered by [Scrapling](https://github.com/D4Vinci/Scrapling):
  - **Fast Mode** — Pure HTTP fetching via `Fetcher` (fastest, for static sites)
  - **Dynamic Mode** — Playwright-based via `DynamicFetcher` (for JS-rendered pages)
  - **Stealth Mode** — Max anti-detection via `StealthyFetcher` (bypasses Cloudflare, WAFs, and bot protection)
  - Auto-fallback: fast → dynamic → stealth if no results found
- **Advanced Anti-Detection** — Scrapling's built-in TLS fingerprinting, CDP leak fix, WebRTC leak fix, canvas noise injection, headless bypass, timezone matching, plus 50+ rotating User-Agents, header randomization, proxy rotation, CAPTCHA detection, exponential backoff
- **Beautiful Dashboard** — Dark-themed UI built with Next.js, shadcn/ui, Recharts, and Framer Motion
- **Job Scheduling** — Run scraping jobs on demand or schedule them with cron expressions
- **Real-time Updates** — WebSocket support for live job progress tracking
- **Data Export** — Export scraped data as CSV or JSON
- **Fully Dockerized** — One command to start everything

## Screenshots

> The frontend works standalone with realistic mock data — just run `npm run dev` to see the full UI.

| Dashboard | Jobs |
|-----------|------|
| Stats, activity charts, recent jobs | Create, manage, and monitor scraping jobs |

| Results | Settings |
|---------|----------|
| Search, filter, and export scraped data | Configure proxies, anti-detection, and exports |

## Tech Stack

### Backend
- **FastAPI** — Async Python web framework
- **SQLAlchemy** + **aiosqlite** — Async SQLite database
- **Scrapling** — Advanced anti-bot scraping framework (3 fetcher modes)
- **httpx** — Async HTTP client
- **Patchright** + **Playwright** — Anti-detection headless browsers for JS-heavy pages
- **APScheduler** — Job scheduling
- **BeautifulSoup4** — HTML parsing

### Frontend
- **Next.js 14** — React framework with App Router
- **shadcn/ui** — Radix UI + Tailwind CSS component library
- **Recharts** — Charting library
- **Framer Motion** — Animations
- **Lucide Icons** — Icon set
- **TypeScript** — Type safety

## Quick Start

### With Docker (Recommended)

```bash
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Manual Setup

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
python -m patchright install chromium
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 in your browser.

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/jobs` | Create a scraping job |
| `GET` | `/api/jobs` | List all jobs |
| `GET` | `/api/jobs/{id}` | Get job details + results |
| `POST` | `/api/jobs/{id}/run` | Run a job immediately |
| `DELETE` | `/api/jobs/{id}` | Delete a job |
| `GET` | `/api/results/{job_id}` | Get scraped results |
| `GET` | `/api/results/{job_id}/export?format=csv` | Export as CSV |
| `GET` | `/api/results/{job_id}/export?format=json` | Export as JSON |
| `GET` | `/api/stats` | Dashboard statistics |
| `WS` | `/ws/jobs/{id}` | Real-time job progress |

## Scraping Modes

| Mode | Fetcher | Best For | Speed |
|------|---------|----------|-------|
| **Fast** | `Fetcher` | Static HTML pages, APIs | Fastest |
| **Dynamic** | `DynamicFetcher` | JS-rendered SPAs, infinite scroll | Medium |
| **Stealth** | `StealthyFetcher` | Cloudflare, DataDome, bot-protected sites | Slowest |

The engine automatically falls back through modes (fast → dynamic → stealth) if no results are found.

## Anti-Detection Features

**Scrapling built-in:**
- TLS fingerprint mimicry
- CDP (Chrome DevTools Protocol) leak fix
- WebRTC leak prevention
- Canvas fingerprint noise injection
- Headless browser detection bypass
- Timezone and locale matching
- Adaptive element tracking (resilient to site layout changes)

**Additional layers:**
- 50+ real browser User-Agent strings
- Randomized request headers (Accept-Language, Accept-Encoding, Sec-Fetch-*)
- Configurable request delays (2-5s default)
- HTTP/SOCKS5 proxy support with rotation
- CAPTCHA detection (reCAPTCHA, hCaptcha, Cloudflare)
- Referer chain simulation
- Exponential backoff with configurable retries
- Cookie and session management

## Project Structure

```
smart-scraper/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry
│   │   ├── api/
│   │   │   ├── routes.py        # All API endpoints
│   │   │   └── schemas.py       # Pydantic models
│   │   ├── scraper/
│   │   │   ├── engine.py        # Core scraping engine
│   │   │   ├── anti_detect.py   # Anti-detection system
│   │   │   ├── parsers.py       # HTML parsing
│   │   │   └── scheduler.py     # Job scheduling
│   │   ├── db/
│   │   │   ├── database.py      # SQLite setup
│   │   │   └── models.py        # DB models
│   │   └── export/
│   │       └── exporter.py      # CSV/JSON export
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js pages
│   │   ├── components/          # React components
│   │   └── lib/                 # Utilities + API client
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## License

MIT

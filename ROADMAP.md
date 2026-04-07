# Smart Scraper Roadmap

## Current State (v1.0)

- 3 scraping modes: fast / dynamic / stealth (with auto-fallback)
- Scrapling anti-detection: TLS fingerprint, CDP fix, WebRTC fix, canvas noise, headless bypass
- Job scheduling with cron expressions
- CSV/JSON export
- Next.js dashboard UI
- Fully dockerized

## Phase 1 — JS Interactions (Priority: High)

Add page interaction support to dynamic/stealth modes so scraper can handle infinite scroll, "Load More" buttons, pagination clicks, and other JS-driven content loading.

**Implementation:**
- Add `interactions` field to `JobCreate` schema
- Support action types: `click`, `scroll`, `wait`, `type`, `select`
- Execute interactions via patchright before extracting data
- Configurable repeat count and delay between actions

**Example:**
```json
{
  "interactions": [
    {"action": "scroll", "to": "bottom", "wait_ms": 2000},
    {"action": "click", "selector": "button.load-more", "repeat": 3, "wait_ms": 1500},
    {"action": "wait", "selector": ".results-loaded", "timeout_ms": 5000}
  ]
}
```

**Files to modify:**
- `backend/app/api/schemas.py` — add `interactions` to `JobCreate`
- `backend/app/db/models.py` — add `interactions` column
- `backend/app/scraper/engine.py` — execute interactions in `_scrapling_fetch`

## Phase 2 — Cookie/Session Injection (Priority: High)

Enable scraping of authenticated pages (LinkedIn, company portals) by injecting browser cookies or reusing Chrome profiles.

**Implementation:**
- Add `cookies` field to `JobCreate` — accepts list of cookie objects or a Netscape cookie file
- Add `browser_profile` option to load an existing Chrome/patchright user data directory
- Cookie import from browser extensions (EditThisCookie JSON format)
- Store cookies encrypted in DB

**Use cases:**
- LinkedIn job listings (login required for full data)
- Internal company job boards
- Sites that gate content behind free accounts

## Phase 3 — CAPTCHA Solving Service (Priority: Medium)

Integrate third-party CAPTCHA solving APIs for automated bypass when scraper encounters challenges.

**Implementation:**
- Add `captcha_config` to settings/job config
- Support providers: 2Captcha, CapSolver, CapMonster
- Auto-detect CAPTCHA type (reCAPTCHA v2/v3, hCaptcha, Cloudflare Turnstile)
- Inject solution token and retry the request
- Budget/rate limiting to control spend

**Cost estimate:** ~$2-3 per 1000 solves

**Files to add:**
- `backend/app/scraper/captcha.py` — CAPTCHA detection + solver integration
- Config for API keys and provider selection

## Phase 4 — LLM Auto-Selector (Priority: Medium, High Value for Freelance)

Use an LLM to automatically analyze page HTML and generate CSS selectors, eliminating manual selector writing for each new site.

**Implementation:**
- New endpoint: `POST /api/jobs/auto-discover`
- Fetch page HTML, truncate to reasonable size
- Send to LLM (local Llama or OpenAI API) with prompt to identify repeating data patterns
- Return suggested selectors for user confirmation
- Cache successful selectors per domain for reuse

**Workflow:**
1. User provides URL only (no selectors)
2. System fetches page, sends HTML structure to LLM
3. LLM returns candidate selectors + sample extracted data
4. User reviews and confirms or adjusts
5. Confirmed selectors saved as site template

**Upwork selling point:** "Handles any website without custom coding"

## Phase 5 — Site Template Library (Priority: Low)

Pre-built selector templates for common job boards and data sources.

**Templates to build:**
- Indeed (stealth mode)
- LinkedIn Jobs (dynamic + cookies)
- Work at a Startup (dynamic)
- Glassdoor (stealth)
- AngelList / Wellfound (dynamic)
- Hacker News Jobs (fast)
- RemoteOK (fast)
- GitHub Jobs (fast)

**Storage:** `backend/templates/{site}.json` with selectors, mode, anti-detection settings, and interaction sequences.

## Phase 6 — Webhook & Notification (Priority: Low)

Push results to external systems when scraping completes.

- Webhook URL per job (POST results on completion)
- Slack/Discord notification integration
- Email alerts for new results matching filters
- Diff detection — only notify on new/changed data

---

## Non-Goals

- Browser GUI for visual selector picking (too complex, existing browser devtools are fine)
- Distributed scraping cluster (overkill for current use cases)
- Built-in proxy pool management (use external proxy services)

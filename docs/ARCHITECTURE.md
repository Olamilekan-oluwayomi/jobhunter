# JobHunter — Architecture

## System overview

```
                    ┌──────────────────────────────────────────────┐
                    │              Frontend (React/Vite)            │
                    │  Dashboard · Jobs explorer · Inputs          │
                    │  TanStack Query caches, retries, mutation    │
                    └───────────────┬──────────────────────────────┘
                                    │  HTTP/JSON  (via nginx in Docker)
                                    ▼
                    ┌──────────────────────────────────────────────┐
                    │              API (FastAPI)                   │
                    │  middleware: request logging · security      │
                    │  headers · rate limiting · CORS             │
                    │  routers: jobs · sources · saved · apps ·    │
                    │  stats · scrape · health                     │
                    │  error handlers (422/404/500 → JSON)         │
                    └──────────┬──────────────────┬────────────────┘
                               │                  │
        ┌──────────────────────▼───┐      ┌───────▼────────────────┐
        │   PostgreSQL             │      │   Scheduler (thread)   │
        │  jobs/sources/saved/     │      │  every N minutes ─ default 60
        │  applications/scrape_runs│      │                       │
        └──────────────────────────┘      └───────┬───────────────┘
                                                  │ fetch
                                        ┌─────────▼──────────┐
                                        │  Scrapers (6)       │
                                        │  thread pool        │
                                        └─────────┬──────────┘
                                                  │ new jobs
                                        ┌─────────▼──────────┐
                                        │  Notifications      │
                                        │  matcher → Discord │
                                        │  matcher → Telegram│
                                        └────────────────────┘
```

## 2. Key flows

### Scraping → persistence → notification

`POST /scrape`, the scheduler, and `jobhunter automate` all call
`run_automation` (`backend/scheduler/jobs.py`):

1. `ScraperManager.fetch_all()` — each scraper runs in its own thread; results
   are deduplicated by URL.
2. New URLs are inserted **per source, in one bulk transaction**
   (`save_jobs_bulk`) — up to ~100x fewer round trips than one insert + commit
   per job. Existing URLs are detected up front (`Job.url IN (...)`).
3. Only genuinely-new jobs are passed to `notify_new_jobs`.
4. Each matching run is recorded in `scrape_runs` (`run_automation` →
   `create_scrape_run`) so recent executions are inspectable via
   `GET /scrape-runs`.
5. The automation feed relayed to the scheduler in FastAPI's lifespan; a plain
   `threading.Thread` loop (no external scheduler dependency) triggers runs on
   an interval and optionally on boot.

### Requests

Every request flows through, in order: CORSMiddleware → RequestLogging →
RateLimit → SecurityHeaders. Each response gets an `x-request-id`, and
failures are normalized to the JSON shape `{"detail": ...}`.

### Searching

`GET /jobs` supports search, filters, pagination and sorting. The API caps
`page_size` at 1000; the dashboard currently loads up to 1000 jobs and does
client-side sorting/filtering for instant interactivity. For datasets much
larger than 1k rows, move filtering to the server (see §5).

## 3. Module map

| Path | Responsibility |
| --- | --- |
| `backend/config.py` | Environment-driven `Settings` (cached, reloadable in tests) |
| `backend/api/main.py` | App assembly, middleware registration, lifespan scheduler |
| `backend/api/middleware.py` | Request logging, security headers, rate limiter |
| `backend/api/errors.py` | Global exception handlers |
| `backend/api/routes/` | REST routers (thin); validation via schemas |
| `backend/api/services/` | Business logic (list/filter/save/search) |
| `backend/api/schemas/` | Pydantic request/response models |
| `backend/database/` | SQLAlchemy models, repository helpers, migrations (alembic) |
| `backend/scrapers/` | One `BaseScraper` subclass per source + manager |
| `backend/notifications/` | Matcher, Discord/Telegram senders, fan-out service |
| `backend/scheduler/` | Automation runner + scrape-run persistence |
| `backend/cli/` | Typer CLI: scrape, automate, scheduler, stats, etc. |
| `backend/utils/` | Logging setup, retry decorator |
| `frontend/src/` | React app; hooks, api client, dashboard + jobs pages, ui kit |

## 4. Cross-cutting concerns

- **Configuration** — single source of truth in `config.Settings`, read from
  the environment. `.env.example` documents every variable.
- **Logging** — `utils.logger.configure_logging` sets a global handler
  (stream + optional rotating file). Request middleware logs one line per
  request with status and duration.
- **Retry** — `utils.retry.retry` applies exponential-backoff retries to
  Discord/Telegram network calls and other flaky I/O.
- **Rate limiting** — in-memory sliding window per client IP. Note: only
  correct for a single API instance; for horizontal scaling move to
  Redis or a shared store.
- **Security** — security headers (nosniff, frame-deny, CSP base),
  `x-request-id`, CORS allow-list (production only uses `CORS_ORIGINS`),
  validation-error responses with no internal details, and a generic 500
  handler that logs the stack trace without echoing it.

## 5. Configuration reference

See `backend/.env.example`. Production specifics:

- `ENVIRONMENT=production` removes local dev origins from the CORS list.
- `RATE_LIMIT_*` tune the request budget.
- `SCHEDULE_*` control automated scraping.
- `DISCORD_WEBHOOK_URL` / `TELEGRAM_BOT_TOKEN`+`TELEGRAM_CHAT_ID` enable
  channels; `MATCH_*` decide what is worth notifying about.
- `UPWORK_TOKEN` enables the Upwork source (skipped otherwise).

## 6. Testing, linting, CI

- `pytest` — hermetic tests (config, matcher, retry, middleware/HTTP via
  TestClient with a stubbed DB session, repository bulk-insert semantics).
  No live DB or network is required.
- `ruff` — rules selected in `pyproject.toml` (`E,F,I,UP,B,SIM,RUF,FURB`);
  `Depends()` in defaults is intentional (FastAPI idiom) and ignored.
- GitHub Actions (`ci.yml`) runs backend lint+test, frontend lint+build, and
  Docker image builds on every push/PR.

## 7. Scaling & extension points

- **Server-side search**: to support very large volumes, add the current
  client-side filters to `GET /jobs` params (company, source, location, remote
  and salary already exist as columns) and page in the dashboard instead of
  fetching 1000.
- **Distributed rate limiting**: swap `RateLimitMiddleware` storage for a
  shared backend (e.g. Redis) keyed by IP.
- **New scraper**: subclass `BaseScraper`, return a list of job dicts with
  the same shape, and register it in `scrapers/manager.py`.
- **New notification channel**: implement a `send_*` in `notifications/`,
  add a `*_enabled` gate in `config.Settings`, and call it in
  `notifications/service.py:notify_new_jobs`.
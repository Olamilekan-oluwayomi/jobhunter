# JobHunter

Aggregate, search and track remote jobs. Scrapes job boards automatically,
exposes a searchable API, and ships a modern dark-mode dashboard.

## Features

- **Automated scraping** — jobicy, arbeitnow, remotive, remoteok, reddit and
  (optional) upwork all run concurrently via a thread pool.
- **Search & filtering** — free-text search across title/company/location/
  description plus sorting and filters in the dashboard.
- **Saved jobs & applications** — track the roles you care about.
- **Notifications** — Discord webhook and Telegram channels with configurable
  keyword/salary/remote matching rules.
- **Health & readiness** endpoints, request logging, security headers and
  per-client-IP rate limiting.
- **Docker Compose** — Postgres + API + nginx-frontend in one command.

## Stack

| Layer | Technology |
| --- | --- |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL, uvicorn |
| Frontend | React 19, Vite 8, Tailwind CSS 4, TanStack Query, React Router 7 |
| Tooling | ruff (lint/format), pytest, oxlint |
| Ops | Docker Compose, GitHub Actions |

## Repository layout

```
backend/        FastAPI application, scrapers, scheduler, notifications
frontend/       React dashboard (Vite + Tailwind)
docker-compose.yml
.github/workflows/ci.yml
```

## Quick start (local)

Requires Python 3.10+ and a running PostgreSQL database.

```bash
# Backend
cd backend
cp .env.example .env        # fill in DB_* credentials
pip install -e . -r requirements.txt
alembic upgrade head
uvicorn api.main:app --reload

# Frontend (in a second terminal)
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` for the dashboard and
`http://localhost:8000/docs` for the API.

Run a one-shot scrape right away:

```bash
jobhunter automate          # fetch + persist + notify once
jobhunter scheduler         # run the automation loop in the foreground
```

## Quick start (Docker)

```bash
cp .env.example .env 2>/dev/null; true
docker compose up --build
```

- Frontend: `http://localhost:8080`
- API docs: `http://localhost:8080/api/docs`
- Health: `http://localhost:8080/api/health` (or `:8000` on the backend)

Set notification and matching options via the compose `environment` block or a
`.env` file at the repo root (see `docker-compose.yml` for variable names).

## Configuration

All behaviour is environment-driven. See
[`backend/.env.example`](backend/.env.example) for the full reference:

- **Matching rules** — a job is notified about when all enabled rules pass:
  `MATCH_KEYWORDS`, `MATCH_SOURCES`, `MATCH_REMOTE_ONLY`, `MATCH_MIN_SALARY`.
- **Channels** define a `DISCORD_WEBHOOK_URL` and/or Telegram
  `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID`.
- **Scheduler** `SCHEDULE_ENABLED`, `SCHEDULE_INTERVAL_MINUTES`,
  `SCHEDULE_RUN_ON_STARTUP`.
- **HTTP hardening** `CORS_ORIGINS`, `TRUSTED_HOSTS`,
  `RATE_LIMIT_ENABLED/REQUESTS/WINDOW_SECONDS`.

## Tests & lint

```bash
cd backend
pytest -q                     # hermetic unit tests (no DB/network needed)
ruff check . && ruff format --check .

cd frontend
npm run lint && npm run build
```

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system overview, data flow
  and extension points.

## License

MIT
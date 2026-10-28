# Jobhunter product roadmap

Status: first implementation milestone, 2026-10-27. Local changes; not deployed.

## Implementation milestone

- Added an isolated interactive `/preview` with For You, Explore, Saved,
  Applications, preferences, light/dark themes and responsive navigation.
- Enabled the live `/saved` and `/applications` screens. Saved roles can be
  explicitly marked as applied; applications support notes, status updates and
  server-side status filtering/pagination. Added `GET /applications`.
- Added nine frontend journey tests and wired them into CI. All pass.
- Added configurable Lever and Ashby integrations with fixture tests. Empty
  board configuration disables both sources. Live source verification remains open.
- Fixed query-parameter and hash-route job deduplication. Backend total: 120 passing tests.
- Updated frontend dependency lockfile within existing ranges. npm audit reports
  zero vulnerabilities, including the new frontend test dependencies.
- Frontend lint/build and backend lint/format checks pass.
- No browser automation surface was available. Visual review and real mobile
  interaction checks remain required; simulated DOM tests do not establish layout quality.

See [design preview](DESIGN-PREVIEW.md) and [company sources](COMPANY-SOURCES.md).

## Baseline results

- Frontend lint and production build: passed.
- Backend: 98 tests passed; Ruff lint and format checks passed.
- Fixed fresh-install database initialization: explicitly select the declared psycopg2 driver for bare postgresql URLs. The installed SQLAlchemy otherwise attempted to import an undeclared psycopg driver. Alembic uses the same normalized URL.
- Initial npm installation reported five high-severity dependency findings; these were resolved in the implementation milestone above.
- Docker is unavailable on this machine. PostgreSQL CLI is installed, but database credentials and an isolated development database have not been configured. Live migrations, end-to-end browser flows, live sources and notification delivery remain unverified.
- Local baseline used Python 3.14 and Node 24; CI declares Python 3.12 and Node 22. Repeat release verification on the CI versions.

Next deliverable: visually verify the prototype, then build authentication and per-user API foundations before connecting the redesigned journeys to live private data.

## Product direction

Help remote developers find eligible roles, understand fit, and manage applications. Initial audience hypothesis: international remote applicants, with useful location support for Nigeria and Africa. Validate with beta users before making marketing claims.

Retain FastAPI, PostgreSQL, React and the existing scraper interface. Build on the current product.

## Audit findings

| Priority | Finding and evidence | Required outcome |
| --- | --- | --- |
| P0 for public beta | API routes have no user authentication; saved jobs, applications and scores are globally unique per job (`database/models.py`). | Accounts, ownership checks and per-user uniqueness; user A cannot access or change user B's private records. |
| P1 | Saved and Applications navigation is disabled (`frontend/src/layout/Sidebar.jsx`). | Working destinations with empty, loading, error and populated states. |
| P1 | Scoring is CLI-driven; automation does not rank and `JobOut` has no score. | Persist profile-based scores and expose ranking plus explanations in the API and UI. |
| P1 | Explorer fetches only 1,000 jobs then filters locally. | Server-side filtering and pagination across the full dataset, with URL-persisted search state. |
| P1 | Application API creates and updates records but has no list route. | Paginated application listing, status history and follow-up dates. |
| P1 | Remote matching is text-based, not country/work-authorization eligibility. | Eligible, restricted and unknown states supported by posting evidence. |
| P1 | Salary matcher does not normalize currencies, monthly pay or k suffixes. | Preserve raw pay, normalize currency and period, and avoid comparing incompatible values. |
| P1 | URL deduplication drops all query parameters (`scrapers/manager.py`). | Preserve identity-bearing parameters while removing known tracking parameters; test distinct jobs on the same path. |
| P2 | Current UI uses very subdued text tokens and a dark-first palette. | Verify contrast; deliver complete light/dark themes and responsive layouts. |

## Delivery sequence and acceptance criteria

1. Baseline: install isolated dependencies, run tests/lint/build, document failures and verify database migrations separately. No live scraping or outbound notifications during baseline testing.
2. Prototype: demonstrate onboarding, For You, job details, Saved and Applications with clearly labelled sample data. Validate desktop and mobile; preserve list position when opening details; support keyboard dismissal and focus restoration.
3. Identity and profile foundation: add user ownership, profile storage and preferences. Migration must preserve existing personal records with explicit ownership assignment. Add cross-user authorization tests before public deployment.
4. Discovery: connect ranking, eligibility evidence and server-side search. Include freshness, source attribution, original application link and uncertainty labels. Scores describe fit, not hiring probability.
5. Application workspace: save, compare, record application, update status, add notes and schedule reminders. Opening an external application must not automatically mark it submitted. Add CV selection and reusable answers.
6. Sources: stabilize current six integrations, then investigate Greenhouse, Lever and Ashby, followed by Workable and Africa-focused boards. Confirm API/feed availability and permitted use before implementation. Add normalization fixtures, timeouts, retry/backoff, source-level health and expiry detection.
7. Beta: verify backup/restore, monitoring, private uploads, account deletion and production configuration. Conduct usability sessions and fix observed blockers before paid launch.

## UX brief

Primary navigation: For You, Explore, Saved, Applications, Profile.

For You should answer "Which jobs deserve my attention today?" Lead with relevant openings and follow-ups, not aggregate database counts. Each result shows title, company, location restrictions, compensation when known, freshness and concise match reasons.

Desktop discovery uses a readable list and detail panel. Mobile uses a dedicated detail view with a clear return path. Persist filters and scroll position. Use visible labels, generous spacing and one accent color; reserve status colors for meaning.

Applications offers board and list views. All actions need feedback and recoverable failure states. Avoid disabled "Soon" navigation in the beta release.

## Release measures

Track onboarding completion, first relevant save, first recorded application, weekly return use and reported irrelevant matches. Source quality measures include successful fetches, unique fresh jobs and eligible matches. Establish targets after observing the beta baseline.

## Deferred

Automatic submissions, generated CVs, recruiter tools and billing follow validation of the core journey. Source names above are candidates, not verified integrations or promised partnerships.

## Verification update � 2026-10-28

The original checkout at C:\Users\hp\jobhunter now passes 120 backend tests,
9 frontend journey tests, backend lint/format checks, frontend lint, and the
production build. Read-only checks against the existing PostgreSQL database
passed for health, jobs, saved jobs and paginated applications. No application
records were changed during these checks.

The local frontend runs at http://127.0.0.1:5176 with the backend on port 8015.
The design preview is at /preview. Scraping and notifications are disabled for
this verification server. These are local development processes, not deployment.

Company-source smoke tests: Linear's public Ashby board returned 32 listed jobs;
Wealthsimple's Lever board returned an empty successful response. No fetched jobs
were persisted and company-board configuration remains opt-in. Visual browser
review remains outstanding because no browser automation surface was available.

Before a public beta: finish accounts and per-user ownership, connect the new
visual design to live profile-based discovery, verify mobile/accessibility in a
browser, and complete deployment/backup checks. The design preview remains an
isolated prototype; the live Saved and Applications pages use real API data.

## Design replacement � 2026-10-28
The new interface is now the main app, backed by live jobs, saved roles and applications. Old URLs redirect into it. No sample jobs are shown on empty or failed API responses. Profile preferences remain local to this browser; account-based profiles remain future work. The old components are retained as inactive source files for now.

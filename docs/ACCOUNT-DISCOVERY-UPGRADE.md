# Account and discovery upgrade

The workspace now requires an account. Preferences, saved jobs and applications
belong to that account. Job listings remain shared public data. Scrape controls
and run history require an administrator.

## Installation and existing data

Back up the database before upgrading. From `backend`, run:

```sh
alembic upgrade head
jobhunter account you@example.com --admin --claim-legacy
```

The command prompts for a password without echoing it. The migration assigns
existing saved jobs and applications to a disabled legacy owner (user 1).
`--claim-legacy` explicitly transfers those records to the named account. Omit
that flag to leave the old records untouched. Registration never claims legacy
data. If the destination already has conflicting records for the same job, the
transfer fails atomically; resolve those duplicates before retrying. Re-running
`account` resets that account's password and invalidates its sessions. Include
`--admin` when retaining administrator access.

CLI tracking commands default to legacy user 1 for backward compatibility. Set
`JOBHUNTER_USER_ID` to the user id printed by `account` to save, track and inspect
that account's records. The CLI is an operator tool with database credentials.
Its environment-profile `match` command uses the same scoring algorithm as web
discovery and keeps its persisted results separate from account score caches.

The account migration intentionally refuses a downgrade that could collapse
multiple users' private rows. Restore a verified backup to roll back the schema.

## Sessions and hosting

Passwords use salted scrypt hashes. Sessions use random opaque tokens, store
only token hashes, expire after seven days and can be revoked by signing out.
Production cookies require HTTPS and are HttpOnly and SameSite=Lax. Keep the
frontend and API on the same site; the supplied `/api` proxy supports this.
Set `ENVIRONMENT=production` and explicit `CORS_ORIGINS` on production hosts.
Do not use wildcard CORS origins for credentialed requests.

Browser writes require `X-Requested-With: JobHunter` and an allowed Origin when
the browser sends one. The client supplies the header automatically. API
responses disable caching to protect private data. Password validation inputs
are excluded from error responses and logs.

Sign-in and registration have a per-process attempt limit. Apply a shared edge
limit for a deployment with multiple API instances. Password reset is currently
an operator CLI action; self-service email recovery and email verification are
not included in this change.

## Discovery and editing

`GET /discovery` supports page/page_size, search, employment_type, eligible_only,
saved_only and sort (`match` or `newest`). It returns 20 jobs by default, up to
100, and omits descriptions until `GET /discovery/{id}` is requested. The browser
keeps filters and pagination in the URL. Applications are also paginated.

Live scores and match explanations come from the backend scorer. Account score
caches refresh in batches only when a job or profile changes. The first request
after a large profile change may take longer while the cache is rebuilt.
Location labels are conservative posting-text evidence, not authorization to
work. Unclear country requirements remain unknown.

Application status changes send only status. Notes save separately, and edits
are queued per application within the browser. Failed drafts remain available
for retry. Updates from separate devices still use last-write-wins semantics.

## Scrapes and notifications

A PostgreSQL advisory lock prevents overlapping automation cycles across CLI,
API and scheduler processes. An overlapping API request returns 409. Scrapes
remain synchronous administrator operations; use the scheduler/CLI for regular
ingestion and avoid relying on long HTTP requests on serverless hosts.

New job inserts use database RETURNING results to identify exact conflict
winners. Matching notification deliveries are inserted in the same transaction
as those jobs. Each job/channel has a unique delivery row. Pending work survives
process restarts and per-run limits; the limit defers work instead of discarding it.

Delivery attempts retry with backoff, up to eight attempts. Due work drains on
automation runs or independently with:

```sh
jobhunter deliver-notifications
jobhunter deliver-notifications --retry-failed
```

Run the first command regularly if notification retries should happen more
frequently than scraping. Provider calls are mocked in automated tests. Delivery
is at least once: a process crash after provider acceptance and before committing
the sent state can repeat a message. Neither provider provides a shared
idempotency key for these calls. Channels remain operator-configured; this
change does not add personal notification destinations.

## Verification

Run backend tests with `pytest -q` and frontend journeys with `npm test`.
`TEST_DATABASE_URL` enables a PostgreSQL integration test that creates and removes
its own UUID-named schema. It verifies fresh migrations, legacy data preservation,
account uniqueness, discovery, exact insertion and cross-connection delivery
locks without modifying existing tables. CI enables this against its test DB.

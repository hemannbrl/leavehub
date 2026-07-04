# leavehub

![CI](https://github.com/hemannbrl/leavehub/actions/workflows/ci.yml/badge.svg)

Leave management API. Employees request time off against a balance; a manager approves
or rejects requests; HR configures leave types, allocations, and holidays.

The API is versioned under `/api/v1/`, paginated, and rate-limited.

## Features

- JWT-authenticated REST API
- Leave requests validated against balance, overlaps, weekends, and holidays
- Request state machine (pending → approved/rejected, with cancel) that adjusts the
  balance on every transition
- Per-employee, per-type, per-year balances tracking accrued / used / pending / carried-over
- Monthly accrual and year-end carry-over via scheduled management commands
- Shared team calendar of approved leave
- Role-based access (employee / manager / hr)
- OpenAPI schema + Swagger UI

## Tech Stack

- Python 3.14, Django 6.0
- Django REST Framework
- SimpleJWT for authentication
- PostgreSQL (`psycopg2-binary`)
- drf-spectacular for the OpenAPI schema
- python-dotenv for `.env` config

## Architecture

Single Django project (`leavehub`) with one app (`leave`). A leave request is the
aggregate; its working-day count excludes weekends and company holidays, and its status
transitions live as methods on the model so the state machine is enforced in one place.
Each transition adjusts the matching `LeaveBalance` in the same transaction, with the
balance row locked so concurrent approvals can't both spend the last day. The interesting
logic is the submit-time validation (balance, overlap, date range). Accrual and carry-over
run outside the request cycle as scheduled management commands. Config is read from
`.env`. See `docs/DESIGN.md` for the full design.

## Running Locally

Requires PostgreSQL running. Start it with `docker compose up -d` (or
`brew services start postgresql@16`); install help is in `docs/TOOLS.md`.

```bash
# from the leavehub/ directory
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# set DJANGO_SECRET_KEY and POSTGRES_PASSWORD in .env

createdb leavehub            # or create the DB however you prefer

python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

API at http://localhost:8000/, admin at `/admin/`, interactive docs at `/api/v1/docs/`.

To exercise the API: register at `/api/v1/auth/register/`, get a JWT at `/api/v1/auth/token/`,
then open `/api/v1/docs/`, click **Authorize**, and paste the access token. (`docs/TOOLS.md` has
a one-line curl token helper.)

## Running Tests

```bash
python manage.py test

# with coverage (fails under 85%)
coverage run manage.py test && coverage report
```

Linting is ruff, run via pre-commit and in CI:

```bash
pip install -r requirements-dev.txt
pre-commit install
ruff check . && ruff format --check .
```

## Deployment

The app serves under gunicorn with WhiteNoise for static files, and ships a `Dockerfile`.

```bash
docker build -t leavehub .
# at deploy time (needs env + DB):
#   python manage.py migrate && python manage.py collectstatic --noinput
#   gunicorn leavehub.wsgi:application --bind 0.0.0.0:8000
```

Before going live, set `DJANGO_DEBUG=False`, real `DJANGO_ALLOWED_HOSTS`, and HTTPS-related
env vars (`DJANGO_SECURE_SSL_REDIRECT=True`, `DJANGO_HSTS_SECONDS`), then confirm a clean
`DJANGO_DEBUG=False python manage.py check --deploy`.

The accrual and carry-over jobs are scheduled, not request-driven — see
`deploy/crontab.example` (monthly `accrue_leave`, year-end `carry_over`), or register the same
two management commands with your platform's scheduler.

## API Endpoints

```
POST   /api/v1/auth/register/                register a user
POST   /api/v1/auth/token/                   obtain JWT
POST   /api/v1/auth/token/refresh/           refresh JWT

GET    /api/v1/leave-types/                  list (hr creates/edits)
POST   /api/v1/leave-types/                  create (hr)

GET    /api/v1/me/balances/                  current user's balances
GET    /api/v1/calendar/                     team calendar (date-range filtered)
GET    /api/v1/leave-requests/               list (role-filtered)
POST   /api/v1/leave-requests/               create
GET    /api/v1/leave-requests/{id}/          retrieve

POST   /api/v1/leave-requests/{id}/approve/  -> approved
POST   /api/v1/leave-requests/{id}/reject/   -> rejected
POST   /api/v1/leave-requests/{id}/cancel/   -> cancelled

GET    /api/v1/schema/                       OpenAPI schema
GET    /api/v1/docs/                         Swagger UI
```

## What I Learned

- **The balance is the thing to protect.** Every status change moves numbers between
  `pending`, `used`, and back, and those moves have to stay consistent with `status`. Keeping
  the transitions as methods on `LeaveRequest` — rather than scattering the arithmetic across
  views — meant there was exactly one place where a balance could change, which made it
  possible to reason about correctness at all.
- **Validation alone doesn't prevent over-booking.** The serializer checks `remaining` without
  a lock, so two requests submitted at once can both pass. The real guard is re-checking under
  `select_for_update()` inside `perform_create`'s transaction; that row lock (Postgres-only,
  inside a transaction) is what actually stops two people spending the same last day.
- **Compute derived values on the server, never trust the client.** `days` comes from the
  `working_days()` helper — weekends and holidays excluded — not from anything the request
  sends. Isolating that as a pure function made it easy to test hard, which mattered because
  everything downstream leans on it.
- **Empty defaults are a real leak.** Filtering the team calendar on a blank `team` would have
  matched every other user with a blank team; returning nothing when `team` is unset was the
  safe default.
- **Some jobs don't belong in the request cycle.** Accrual and carry-over are periodic, not
  user-triggered, so they're management commands run by cron — no Celery needed for this scope.

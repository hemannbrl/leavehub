# leavehub

Leave management API. Employees request time off against a balance; a manager approves
or rejects requests; HR configures leave types, allocations, and holidays.

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

API at http://localhost:8000/, admin at `/admin/`, interactive docs at `/api/docs/`.

To exercise the API: register at `/api/auth/register/`, get a JWT at `/api/auth/token/`,
then open `/api/docs/`, click **Authorize**, and paste the access token. (`docs/TOOLS.md` has
a one-line curl token helper.)

## Running Tests

```bash
python manage.py test
```

## API Endpoints

```
POST   /api/auth/register/                register a user
POST   /api/auth/token/                   obtain JWT
POST   /api/auth/token/refresh/           refresh JWT

GET    /api/leave-types/                  list (hr creates/edits)
POST   /api/leave-types/                  create (hr)

GET    /api/me/balances/                  current user's balances
GET    /api/calendar/                     team calendar (date-range filtered)
GET    /api/leave-requests/               list (role-filtered)
POST   /api/leave-requests/               create
GET    /api/leave-requests/{id}/          retrieve

POST   /api/leave-requests/{id}/approve/  -> approved
POST   /api/leave-requests/{id}/reject/   -> rejected
POST   /api/leave-requests/{id}/cancel/   -> cancelled

GET    /api/schema/                       OpenAPI schema
GET    /api/docs/                         Swagger UI
```

## What I Learned

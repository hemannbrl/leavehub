# leavehub — tools

Everything you need to install, run, and know about the external tools this project uses. On
this machine they're **all already installed** — the install lines are here for reproducing the
setup elsewhere. For each tool: what it's for, how to install, how to verify, the commands
you'll use, and when in the build you need it.

Config-level tools (ruff, pre-commit, coverage, Docker Compose, CI) are in `ENGINEERING.md`;
git and the GitHub CLI are in `GIT_GUIDE.md`. This doc covers the runtime, the database, and
scheduling.

## Map: tool → what for → first needed

| tool | what for | first needed | docs |
|------|----------|--------------|------|
| Python 3.14 + venv + pip | run Django, install deps | Phase 0 | here |
| PostgreSQL | the database | Phase 0 | here |
| Docker + Compose | run Postgres without a native install | Phase 0 (optional) | here + `ENGINEERING.md` §7 |
| cron / scheduler | run accrual + carry-over jobs | Phase 8 / 12 | here |
| curl | manual endpoint checks | Phase 4 on | here |
| git + gh | version control + GitHub | Phase 0 | `GIT_GUIDE.md` |
| ruff / pre-commit / coverage | lint, format, hooks, coverage | Phase 0 (tooling) | `ENGINEERING.md` §3–§5 |

No Celery/Redis here — the scheduled jobs are plain Django management commands run by cron.

## Decide first: native Postgres vs Docker

You need Postgres running — pick one:
- **Docker (recommended):** `docker compose up -d` starts Postgres as `postgres`/`postgres`,
  DB `leavehub`, matching `.env`. See `ENGINEERING.md` §7.
- **Native (Homebrew):** install Postgres as a service (note the role gotcha below).

---

## Python, venv, pip

Already set up (`.venv` with deps installed). Day to day:
```bash
source .venv/bin/activate
python manage.py <command>
pip install -r requirements.txt
deactivate
```
Recreate:
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

## PostgreSQL

**What for:** the database. **Needed from Phase 0.**

**Install (already present):**
```bash
brew install postgresql@16
brew services start postgresql@16
```
**Create the database** (match `POSTGRES_DB` in `.env`, default `leavehub`):
```bash
createdb leavehub
```
**Verify / connect:**
```bash
pg_isready
psql leavehub        # \dt lists tables, \q quits
```

> **Gotcha (native installs):** Homebrew Postgres makes a superuser named after your macOS
> account with no password, but `.env` defaults to `postgres`/`postgres`. Either create the
> role — `psql postgres -c "CREATE ROLE postgres LOGIN SUPERUSER PASSWORD 'postgres';"` — or
> edit `.env` to your local user. The **Docker** Postgres avoids this (it's `postgres`/
> `postgres` out of the box).

Common errors: *role/password* → the gotcha above. *can't connect 5432* → Postgres isn't
running.

## Docker & Docker Compose

**What for:** run Postgres as a container instead of natively. **Optional but recommended**,
from Phase 0.

```bash
docker --version
docker compose up -d        # start Postgres (docker-compose.yml, ENGINEERING.md §7)
docker compose ps
docker compose down         # add -v to wipe the volume
```

## cron / scheduler

**What for:** the accrual and carry-over jobs aren't request-driven — they're management
commands that must run on a schedule. **Built in Phase 8, scheduled for real in Phase 12.**

Run them by hand any time:
```bash
python manage.py accrue_leave     # add monthly accrual
python manage.py carry_over       # roll balances into next year
```

Schedule them in production:
- **Local/server cron** (`crontab -e`):
  ```cron
  # monthly accrual at 02:00 on the 1st
  0 2 1 * * cd /path/to/leavehub && /path/to/.venv/bin/python manage.py accrue_leave
  # carry-over at 00:30 on Jan 1
  30 0 1 1 * cd /path/to/leavehub && /path/to/.venv/bin/python manage.py carry_over
  ```
- **Platform scheduler:** Render Cron Jobs, Railway cron, or a scheduled GitHub Action that
  runs the same command. See `ENGINEERING.md` §10.

## curl

**What for:** manual endpoint checks (the **Verify (manual)** blocks in `BUILD_ORDER.md`).
Token helper:
```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/token/ \
  -d 'username=joe&password=secret123' \
  | python -c "import sys,json;print(json.load(sys.stdin)['access'])")
curl -s localhost:8000/api/me/balances/ -H "Authorization: Bearer $TOKEN"
```

## git, GitHub CLI, and the dev toolchain

- **git + gh** (installed, gh authenticated as `hemannbrl`): per-phase branch → PR workflow in
  `GIT_GUIDE.md`.
- **ruff / pre-commit / coverage:** from `requirements-dev.txt`; config + usage in
  `ENGINEERING.md` §3–§5.

---

## Fresh-machine setup (from zero)

```bash
# 1. system tools
brew install postgresql@16 git gh
brew install --cask docker            # if you'll use Docker for Postgres

# 2. database (choose ONE)
brew services start postgresql@16     # native, or:
docker compose up -d                  # Docker

# 3. project
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                  # set SECRET_KEY + POSTGRES_PASSWORD
createdb leavehub                     # skip if using Docker Postgres
python manage.py migrate
python manage.py runserver
```

# Deployment

## Configuration

All configuration is environment-driven (loaded from `.env` in development — see
`.env.example`). No secret is committed.

| variable | purpose | dev default |
|----------|---------|-------------|
| `DJANGO_SECRET_KEY` | Django signing key — generate per environment | *(required)* |
| `DJANGO_DEBUG` | `True`/`False` | `False` |
| `DJANGO_ALLOWED_HOSTS` | comma-separated hosts | *(empty)* |
| `POSTGRES_DB/USER/PASSWORD/HOST/PORT` | database | `leavehub`/`postgres`/…/`localhost`/`5432` |
| `DJANGO_SECURE_SSL_REDIRECT` | force HTTPS behind the proxy | `False` |
| `DJANGO_HSTS_SECONDS` | HSTS max-age | `0` |

## Local development

```bash
docker compose up -d                  # Postgres 16
pip install -r requirements.txt -r requirements-dev.txt
cp .env.example .env                  # set SECRET_KEY and POSTGRES_PASSWORD
python manage.py migrate
python manage.py createcachetable     # shared cache table (throttle counters)
python manage.py seed_demo            # demo org — all passwords leavehub123
python manage.py runserver            # web UI at /, Swagger at /api/v1/docs/
```

## Production

Ships as a container (see `Dockerfile`): `python:3.14-slim`, gunicorn on `:8000`,
WhiteNoise serving static files. Run migrations, the cache table, and collectstatic at
**deploy** time, not build time:

```bash
docker build -t leavehub .
# at deploy:
python manage.py migrate
python manage.py createcachetable
python manage.py collectstatic --noinput
gunicorn leavehub.wsgi:application --bind 0.0.0.0:8000
```

The throttle counters live in the database cache (`django_cache` table), so they're
shared across gunicorn workers without extra infrastructure.

### Scheduled jobs

Accrual and carry-over are management commands, not request-driven — run them on a
schedule (see `deploy/crontab.example`, or a PaaS scheduler):

```
10 0 1 * *   python manage.py accrue_leave    # monthly grant, 1st of the month
30 0 1 1 *   python manage.py carry_over      # roll balances into the new year, Jan 1
```

### Security posture

With `DJANGO_DEBUG=False`, secure cookies switch on automatically; set
`DJANGO_SECURE_SSL_REDIRECT=True` and `DJANGO_HSTS_SECONDS` (e.g. `31536000`) behind
TLS. Verify a clean:

```bash
DJANGO_DEBUG=False python manage.py check --deploy
```

The API is versioned (`/api/v1/`), paginated, and throttled out of the box.

## Free-tier deployment (Render + Neon)

The public demo runs on free tiers:

- **Web** — Render free web service from `render.yaml` (Docker; `deploy/render-start.sh`
  migrates, creates the cache table, collects static, reseeds the demo org when
  `SEED_ON_BOOT=true`, then runs gunicorn). Render's hostname is trusted automatically
  via `RENDER_EXTERNAL_HOSTNAME`.
- **Postgres** — Neon (`POSTGRES_SSLMODE=require`).
- **Scheduled jobs** — accrual is monthly and carry-over yearly, so on the free demo
  they're run by hand when needed (`python manage.py accrue_leave`); on real
  infrastructure use the crontab above.

Free-tier behavior: the instance sleeps when idle (first request takes ~30s) and the
demo org reseeds on each boot.

## CI

`.github/workflows/ci.yml` runs ruff lint + format check, migrations, and the test
suite with coverage against a real Postgres service container on every push and PR.
Pre-commit hooks enforce the same locally: `pre-commit install`.

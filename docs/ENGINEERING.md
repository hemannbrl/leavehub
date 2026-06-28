# leavehub — engineering & production guide

The conventions that make this repo look like professional work rather than a tutorial: how
it's bootstrapped, how code is kept clean, how it's tested in CI, how services run, and what
to do before it could go to production.

`BUILD_ORDER.md` references this doc in two places: **Phase 0** (scaffold + tooling) and
**Phase 12** (production hardening). Set up the tooling (sections 2–6) right after the
scaffold, so every PR from Phase 1 onward is linted and tested automatically.

---

## 1. Project layout

```
leavehub/
  leavehub/            # project package: settings, urls, wsgi, asgi
  leave/               # the app: models, serializers, views, permissions, calendar,
                       #          management/commands, tests/
  docs/                # STATUS, DESIGN, DATABASE, BUSINESS_LOGIC, TOOLS, BUILD_ORDER,
                       #   GIT_GUIDE, ENGINEERING
  .env / .env.example  # config (real values gitignored; template committed)
  requirements.txt     # runtime deps (pinned)
  requirements-dev.txt # tooling deps
  pyproject.toml       # ruff + coverage config
  .pre-commit-config.yaml
  docker-compose.yml   # local Postgres
  Dockerfile           # production image
  manage.py
```

Configuration is environment-driven (`python-dotenv` loads `.env`); no secret is ever
committed.

## 2. Dependencies

Pin runtime deps so installs are reproducible:
```bash
pip freeze > requirements.txt    # or hand-pin the top-level packages with ==
```

**File: `requirements-dev.txt`**
```
ruff
pre-commit
coverage
```

## 3. Code style & linting (ruff)

[ruff](https://docs.astral.sh/ruff/) is one fast tool that replaces flake8 + isort +
pyupgrade and also formats. Configure it in `pyproject.toml`.

**File: `pyproject.toml`**
```toml
[tool.ruff]
line-length = 100
extend-exclude = ["migrations"]

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "DJ"]  # pycodestyle, pyflakes, isort, pyupgrade, bugbear, django

[tool.coverage.run]
source = ["."]
omit = ["*/migrations/*", "*/tests/*", "manage.py", "*/settings.py",
        "*/wsgi.py", "*/asgi.py", ".venv/*"]

[tool.coverage.report]
show_missing = true
fail_under = 85
```
```bash
ruff check .          # lint (--fix to autofix)
ruff format .         # format
ruff format --check . # CI check
```

## 4. Pre-commit hooks

**File: `.pre-commit-config.yaml`**
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.6          # pin to the latest release
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```
```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

## 5. Testing & coverage

```bash
coverage run manage.py test
coverage report          # fails under fail_under
coverage html            # htmlcov/ (gitignored)
```
Add `htmlcov/` and `.coverage` to `.gitignore`.

## 6. Continuous integration (GitHub Actions)

Every PR and push to `main` runs lint + format-check + migrations + tests against real
Postgres.

**File: `.github/workflows/ci.yml`**
```yaml
name: CI

on:
  pull_request:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: leavehub
          POSTGRES_USER: postgres
          POSTGRES_PASSWORD: postgres
        ports: ["5432:5432"]
        options: >-
          --health-cmd pg_isready --health-interval 10s
          --health-timeout 5s --health-retries 5
    env:
      DJANGO_SECRET_KEY: ci-not-a-real-secret
      DJANGO_DEBUG: "False"
      DJANGO_ALLOWED_HOSTS: localhost,127.0.0.1
      POSTGRES_DB: leavehub
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_HOST: localhost
      POSTGRES_PORT: "5432"
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.14"
      - run: pip install -r requirements.txt -r requirements-dev.txt
      - run: ruff check .
      - run: ruff format --check .
      - run: python manage.py migrate
      - run: coverage run manage.py test && coverage report
```
Public-repo badge: `![CI](https://github.com/hemannbrl/leavehub/actions/workflows/ci.yml/badge.svg)`.

## 7. Local services (Docker Compose)

**File: `docker-compose.yml`**
```yaml
services:
  db:
    image: postgres:16
    environment:
      POSTGRES_DB: leavehub
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]

volumes:
  pgdata:
```
```bash
docker compose up -d
docker compose down        # add -v to wipe the volume
```

## 8. API conventions for production

Added in **Phase 12** so they don't complicate the early phases.

- **Versioning:** mount the API under `/api/v1/`.
- **Pagination:** page-number pagination globally. *Changes list responses* to
  `{"count","next","previous","results"}`, so tests doing `len(r.data)` must switch to
  `r.data["results"]` (the balances and calendar list tests).
- **Throttling:** per-user / per-anon rate limits.

```python
REST_FRAMEWORK = {
    # ... existing auth/permissions/schema keys ...
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"user": "1000/day", "anon": "20/hour"},
}
```

## 9. Security checklist (before production)

```python
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = os.getenv("DJANGO_SECURE_SSL_REDIRECT", "False") == "True"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_HSTS_SECONDS", "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
```
```bash
DJANGO_DEBUG=False python manage.py check --deploy
```
Checklist: `DEBUG=False`, real `ALLOWED_HOSTS`, `SECRET_KEY` from env (already), HTTPS + secure
cookies + HSTS, rotate any secret that ever touched a commit. If a browser frontend calls the
API, add `django-cors-headers`.

## 10. Static files & deployment

Static via [WhiteNoise](https://whitenoise.readthedocs.io/) under gunicorn:
```python
STATIC_ROOT = BASE_DIR / "staticfiles"
# add "whitenoise.middleware.WhiteNoiseMiddleware" right after SecurityMiddleware
STORAGES = {"staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}}
```
Add `gunicorn` and `whitenoise` to `requirements.txt`.

**File: `Dockerfile`**
```dockerfile
FROM python:3.14-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# migrate and collectstatic run at deploy time (they need env/DB), not at build:
#   python manage.py migrate && python manage.py collectstatic --noinput
CMD ["gunicorn", "leavehub.wsgi:application", "--bind", "0.0.0.0:8000"]
```

**Scheduled jobs in production:** the `accrue_leave` and `carry_over` management commands
aren't request-driven — schedule them. On a server use cron; on a platform use its scheduler
(Render Cron Jobs, Railway cron, a scheduled GitHub Action) to run, e.g., `accrue_leave`
monthly and `carry_over` at year end.

Deploy flow: set env vars, `migrate`, `collectstatic`, start gunicorn, register the scheduled
commands.

---

## Definition of "production-ready" for this repo

- [ ] ruff clean (`ruff check .` and `ruff format --check .`)
- [ ] pre-commit installed and passing
- [ ] tests green with coverage ≥ 85%
- [ ] CI passing on the PR
- [ ] `python manage.py check --deploy` clean with `DEBUG=False`
- [ ] API versioned, paginated, throttled
- [ ] accrual + carry-over scheduled in the target environment
- [ ] `docker compose up` brings up Postgres; the app runs against it
- [ ] README complete

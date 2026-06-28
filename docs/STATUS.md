# leavehub — status

What's been done on this project, in detail. This is a planning/build exercise: leavehub is
**fully scaffolded and documented, but not yet built or committed**. The domain code
(`models.py`, `views.py`, `serializers.py`, …) is still empty — building it phase by phase
from `BUILD_ORDER.md` is the remaining work.

Last updated: 2026-06-28.

## What it is
A leave & attendance management API: employees request time off, managers approve/reject, HR
oversees policy. The deceptively tricky part is **balance accounting and validation**. It's the
smallest scope of the three projects — a clean one to finish.

## Environment
- **Location:** `/Users/hemantbaral/projects/cv_projects/leavehub/` (run commands from here;
  it has `manage.py`).
- **Stack:** Python 3.14.3, Django 6.0.6, DRF, SimpleJWT, PostgreSQL (`psycopg2-binary`),
  python-dotenv, drf-spectacular. No Celery/Redis — the scheduled jobs are management commands.
  All installed in `.venv`.
- **Config:** env-driven via `python-dotenv`. Real `.env` (generated `SECRET_KEY` + Postgres
  creds, gitignored) and committed `.env.example`. No secrets committed.
- **Git:** own repo on branch `main`, **no commits and no GitHub remote yet**. Identity
  `Hemannbrl <hemann.brl@gmail.com>`; `gh` authenticated as **hemannbrl**.
- **To run:** a local Postgres DB `leavehub` at `localhost:5432` (user/pass `postgres`/
  `postgres`, or edit `.env`).

## Done
- Scaffold: `leavehub/` project package, `leave/` app, env-driven `settings.py`,
  DRF/JWT/spectacular configured. Verified `manage.py check` passes.
- All 8 docs in `docs/`, written and reviewed:
  - `STATUS.md` — this file (overview + handoff).
  - `DESIGN.md` — rationale, models, open decisions.
  - `DATABASE.md` — the tables.
  - `BUSINESS_LOGIC.md` — the rules acting on the tables.
  - `TOOLS.md` — install / run / verify every external tool.
  - `BUILD_ORDER.md` — the step-by-step build (Phases 0–12, full code + tests). **Start here.**
  - `GIT_GUIDE.md` — the per-phase branch → PR workflow.
  - `ENGINEERING.md` — linting, pre-commit, CI, Docker, production hardening.

## Not done
- Any domain code (models/serializers/views/permissions/calendar/management commands),
  migrations, tests.
- The first commit, the GitHub repo, and the tooling files (`pyproject.toml`,
  `.pre-commit-config.yaml`, `.github/workflows/ci.yml`, `docker-compose.yml`, `Dockerfile`)
  — written out in `ENGINEERING.md` but not yet created; add them in Phase 0.

## Models (planned — see DATABASE.md)
- `Profile` — role: employee / manager / hr, `manager` FK (who approves), `team`.
- `LeaveType` — `default_allocation_days`, `accrual_per_month`, `max_carry_over_days`,
  `paid`, `requires_approval`.
- `LeaveBalance` — accrued / used / pending / carried_over, unique per (employee, type, year);
  `remaining = accrued + carried_over − used − pending` (a property, not a column).
- `LeaveRequest` — status pending/approved/rejected/cancelled, `days`, dates, approver.
- `Holiday` — dates excluded from the working-day count.

## Build path (BUILD_ORDER.md, Phases 0–12)
0 scaffold → 1 roles → 2 leave types & balances → 3 holidays & `working_days()` counter →
4 JWT auth → 5 leave request + validation (dates, balance, overlap) + reserve-pending →
6 approve/reject/cancel transitions with row-locked balance math → 7 balances + team calendar →
(+ leave-types endpoint) → 8 accrual + carry-over management commands → 9 OpenAPI docs →
10 test gaps → 11 README/polish →
12 production hardening. Each phase = one feature branch + one PR + one commit, tests first.

## Key points to preserve
- Transitions are methods on `LeaveRequest` that adjust the `select_for_update()`-locked
  balance row in one transaction; the balance effect must stay consistent with status.
- `perform_create` re-checks `remaining` under the lock (the serializer validates it unlocked)
  to close a create-time over-booking race (fixed during review).
- `working_days()` excludes weekends + company holidays — it's the helper everything leans on.
- Cancel is owner/HR-only; the calendar returns nothing when `team` is blank (both fixed during
  review).
- Accrual + carry-over are management commands (no Celery), scheduled by cron in production.
- All code in the docs was reviewed by reading, **not executed** — the per-phase `Run`/`Verify`
  steps are where it gets proven.

## What's left
1. Phase 0 git steps: first commit + `gh repo create` (see `GIT_GUIDE.md`), plus adding the
   tooling files from `ENGINEERING.md`.
2. Build Phases 1–12 from `BUILD_ORDER.md`.

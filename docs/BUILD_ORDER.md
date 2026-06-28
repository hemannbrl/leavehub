# leavehub — build order

Slice-by-slice plan. Every phase states its goal, names the files it touches with full code,
shows how to verify it by hand, gives the tests, the commands to run, a done-when checklist,
and the commit it ends on. Build in order. Matches `DATABASE.md` and `BUSINESS_LOGIC.md`.
Balances and the day counter come before requests, because a request can't validate without
them. Engineering practice (linting, pre-commit, CI, Docker, production hardening) lives in
`ENGINEERING.md`, set up in Phase 0 and applied in Phase 12.

> Per phase: start from an updated `main` on a new branch
> (`git checkout -b feature/phase-<n>-<name>`), make the changes, write the tests, run them,
> then commit, push, and open a PR with the message at the end of the phase. Full git steps
> are in `GIT_GUIDE.md`.

## How to read this doc

- **(replace the file)** — the block is the whole file. **(add ...)** — append/insert into
  the existing file; new `import` lines go with the others at the top.
- Each phase ends green: migrations applied and `python manage.py test` passing before you
  commit.
- Tests live in a `tests/` package (created in Phase 1). `TestCase` for model/logic,
  `APITestCase` for endpoints.
- **Tools** — how to install, run, and verify every external tool (Postgres, Docker, cron, curl)

  is in `TOOLS.md`. Set up the services there before Phase 0.
- **Manual checks** assume `python manage.py runserver` is up in another terminal and
  Postgres is running. The token helper saves an access token to `$TOKEN`:

```bash
TOKEN=$(curl -s -X POST localhost:8000/api/auth/token/ \
  -d 'username=joe&password=secret123' \
  | python -c "import sys,json;print(json.load(sys.stdin)['access'])")
```

- **The balance is the thing to protect.** Every status change moves numbers
  (`pending`/`used`), and those moves must stay consistent with `status`. That's why the
  transition tests matter most and why the locking notes appear throughout.

## Phase overview

| phase | branch | delivers | commit |
|-------|--------|----------|--------|
| 1 | feature/phase-1-roles | Profile (role, manager, team) | `add profile model with role and manager` |
| 2 | feature/phase-2-balances | LeaveType + LeaveBalance | `add leave type and balance models` |
| 3 | feature/phase-3-day-count | Holiday + working-day counter | `add holidays and working-day counter` |
| 4 | feature/phase-4-auth | JWT register/login | `wire up jwt auth and registration` |
| 5 | feature/phase-5-leave-request | request create + validation + reserve | `leave request create with balance and overlap validation` |
| 6 | feature/phase-6-transitions | approve/reject/cancel + balance math | `approve/reject/cancel with locked balance updates` |
| 7 | feature/phase-7-views | balances, team calendar, leave types | `balances and team calendar endpoints` |
| 8 | feature/phase-8-accrual | accrual + carry-over commands | `accrual and carry-over management commands` |
| 9 | feature/phase-9-docs | OpenAPI schema + Swagger | `expose openapi schema and swagger ui` |
| 10 | feature/phase-10-tests | coverage round-out | `round out test coverage` |
| 11 | feature/phase-11-polish | README + notes | `flesh out readme and notes` |
| 12 | feature/phase-12-hardening | versioning, pagination, throttling, deploy config | `harden for production` |

Tooling & CI (ruff, pre-commit, GitHub Actions, Docker) is set up in Phase 0 from
`ENGINEERING.md` — do it before Phase 1 so every PR is linted and tested.

## Phase 0 — scaffold

**Goal:** a runnable Django + DRF project wired to Postgres via `.env`, with JWT and OpenAPI —
plus the dev tooling and CI from `ENGINEERING.md`. Already on `main`; the steps below are how
it was built, so the repo is reproducible from scratch.

**Bootstrap**
```bash
mkdir leavehub && cd leavehub
python3 -m venv .venv && source source .venv/bin/activate
pip install --upgrade pip
```

**File: `requirements.txt`** (then install + scaffold)
```
Django
djangorestframework
djangorestframework-simplejwt
psycopg2-binary
python-dotenv
drf-spectacular
```
```bash
pip install -r requirements.txt
django-admin startproject leavehub .
python manage.py startapp leave
```

**Settings** — convert `leavehub/settings.py` to read from the environment (full file is in
the repo):
```python
from pathlib import Path
import os
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ["DJANGO_SECRET_KEY"]
DEBUG = os.getenv("DJANGO_DEBUG", "False") == "True"
ALLOWED_HOSTS = [h for h in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",") if h]

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "rest_framework", "drf_spectacular", "leave",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("POSTGRES_DB", "leavehub"),
        "USER": os.getenv("POSTGRES_USER", "postgres"),
        "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
        "HOST": os.getenv("POSTGRES_HOST", "localhost"),
        "PORT": os.getenv("POSTGRES_PORT", "5432"),
    }
}

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ("rest_framework_simplejwt.authentication.JWTAuthentication",),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}
SPECTACULAR_SETTINGS = {"TITLE": "leavehub API", "VERSION": "0.1.0", "SERVE_INCLUDE_SCHEMA": False}
```

**Config & ignore**

**File: `.env.example`** (committed template; copy to `.env` and fill in)
```
DJANGO_SECRET_KEY=
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
POSTGRES_DB=leavehub
POSTGRES_USER=postgres
POSTGRES_PASSWORD=
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```
```bash
cp .env.example .env
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
# paste as DJANGO_SECRET_KEY; set POSTGRES_PASSWORD
```

**File: `.gitignore`** — ignore `.venv/`, `.env`, `db.sqlite3`, `__pycache__/`, `*.py[cod]`,
`staticfiles/`, `htmlcov/`, `.coverage`, `.DS_Store`.

**Bring up services and verify** (install/run details for every tool are in `TOOLS.md`)
```bash
docker compose up -d                 # Postgres (ENGINEERING.md §7)
python manage.py migrate
python manage.py runserver           # http://localhost:8000/admin/ should load
```

**Tooling & CI** — before Phase 1, add from `ENGINEERING.md`: `requirements-dev.txt` (§2),
`pyproject.toml` ruff + coverage (§3), `.pre-commit-config.yaml` (§4) then `pre-commit install`,
and `.github/workflows/ci.yml` (§6).

**Done when:** `runserver` boots against Postgres, `ruff check .` is clean, and
`pre-commit run --all-files` passes. Commit the scaffold + tooling on `main`, then create the
GitHub repo (`GIT_GUIDE.md`).
> `initial Django scaffold for leavehub`

---

## Phase 1 — roles

**Goal:** every user has a `Profile` with a role (employee / manager / hr), a `manager` link
(who approves their leave), and a `team` (for the calendar). Created automatically per user.

**Why now:** the role and the `manager` link drive every queryset and permission later.

**File: `leave/models.py`** (replace the file)
```python
from django.conf import settings
from django.db import models


class Profile(models.Model):
    class Role(models.TextChoices):
        EMPLOYEE = "employee", "Employee"
        MANAGER = "manager", "Manager"
        HR = "hr", "HR"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYEE)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="reports",
    )
    team = models.CharField(max_length=80, blank=True)

    def __str__(self):
        return f"{self.user} ({self.role})"
```

**File: `leave/signals.py`** (new)
```python
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
```

**File: `leave/apps.py`** (replace the file)
```python
from django.apps import AppConfig


class LeaveConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "leave"

    def ready(self):
        from . import signals  # noqa: F401
```

**File: `leave/admin.py`** (replace the file)
```python
from django.contrib import admin

from .models import Profile

admin.site.register(Profile)
```

**Migration:** `0001_initial` creates `leave_profile` (one-to-one to `auth_user`, plus
`role`, a self-referential `manager` FK, and `team`).

**Verify (manual):**
```bash
python manage.py createsuperuser
python manage.py shell -c "from django.contrib.auth import get_user_model as g; \
print(g().objects.first().profile.role)"
# -> employee
```

### Tests
Delete the default `leave/tests.py` and start the package.

**File: `leave/tests/__init__.py`** (new, empty)

**File: `leave/tests/test_profile.py`** (new)
```python
from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class ProfileTests(TestCase):
    def test_profile_created_with_user(self):
        user = User.objects.create_user("a", password="x")
        self.assertEqual(user.profile.role, "employee")
```

**Run**
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py test
```

**Done when:** the migration is applied, every new user gets a profile, the test passes.
> `add profile model with role and manager`

---

## Phase 2 — leave types and balances

**Goal:** the policy table (`LeaveType`) and the per-employee, per-type, per-year balance
(`LeaveBalance`) exist, with `remaining` derived from its counters.

**Why now:** a leave request validates against a balance, so the balance must exist first.

**File: `leave/models.py`** (add below `Profile`)
```python
class LeaveType(models.Model):
    name = models.CharField(max_length=40)
    default_allocation_days = models.DecimalField(max_digits=5, decimal_places=2)
    accrual_per_month = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    paid = models.BooleanField(default=True)
    requires_approval = models.BooleanField(default=True)
    max_carry_over_days = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def __str__(self):
        return self.name


class LeaveBalance(models.Model):
    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="balances"
    )
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    year = models.PositiveIntegerField()
    accrued = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    used = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    pending = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    carried_over = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    class Meta:
        unique_together = ("employee", "leave_type", "year")

    @property
    def remaining(self):
        return self.accrued + self.carried_over - self.used - self.pending
```

**File: `leave/admin.py`** (replace the file)
```python
from django.contrib import admin

from .models import LeaveBalance, LeaveType, Profile

admin.site.register(Profile)
admin.site.register(LeaveType)
admin.site.register(LeaveBalance)
```

**Migration:** adds `leave_leavetype` and `leave_leavebalance` (with the
`(employee, leave_type, year)` unique constraint). `remaining` is a Python property, so it is
**not** a column.

**Verify (manual):** in admin, add a `LeaveType` (e.g. "annual", allocation 20) and a
`LeaveBalance` for your user — you'll need these to create requests in Phase 5.

### Tests
**File: `leave/tests/test_balance.py`** (new)
```python
from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase

from leave.models import LeaveBalance, LeaveType

User = get_user_model()


class BalanceTests(TestCase):
    def test_remaining_is_accrued_plus_carried_minus_used_and_pending(self):
        user = User.objects.create_user("e", password="x")
        lt = LeaveType.objects.create(name="annual", default_allocation_days=20)
        bal = LeaveBalance.objects.create(
            employee=user, leave_type=lt, year=date.today().year,
            accrued=20, carried_over=5, used=4, pending=1,
        )
        self.assertEqual(bal.remaining, 20)
```

**Run**
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py test
```

**Done when:** both tables exist, the unique constraint is in the migration, the `remaining`
test passes.
> `add leave type and balance models`

---

## Phase 3 — holidays and day counting

**Goal:** a `Holiday` table and a pure `working_days(start, end)` helper that skips weekends
and holidays.

**Why now:** the request's `days` (and therefore all balance math) comes from this helper, so
it must be rock-solid before requests use it.

**File: `leave/models.py`** (add)
```python
class Holiday(models.Model):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=80)

    def __str__(self):
        return f"{self.date} {self.name}"
```

**File: `leave/calendar.py`** (new)
```python
from datetime import timedelta

from .models import Holiday


def working_days(start, end):
    holidays = set(Holiday.objects.values_list("date", flat=True))
    count = 0
    day = start
    while day <= end:
        if day.weekday() < 5 and day not in holidays:   # Mon-Fri, not a holiday
            count += 1
        day += timedelta(days=1)
    return count
```

**File: `leave/admin.py`** — register the new model (merge the import line):
```python
from .models import Holiday, LeaveBalance, LeaveType, Profile
admin.site.register(Holiday)
```

**Migration:** adds `leave_holiday` (unique `date`).

**Verify (manual):**
```bash
python manage.py shell -c "from datetime import date; from leave.calendar import working_days; \
print(working_days(date(2026,6,1), date(2026,6,5)))"
# Mon 2026-06-01 .. Fri 2026-06-05 -> 5
```

### Tests
The whole app leans on this helper, so test it hard. The tests compute a real Monday rather
than hardcoding a weekday, so they don't depend on the calendar.

**File: `leave/tests/test_calendar.py`** (new)
```python
from datetime import date, timedelta

from django.test import TestCase

from leave.calendar import working_days
from leave.models import Holiday


class WorkingDaysTests(TestCase):
    def setUp(self):
        self.monday = date(2026, 6, 1)
        while self.monday.weekday() != 0:        # find a real Monday
            self.monday += timedelta(days=1)
        self.sunday = self.monday + timedelta(days=6)

    def test_full_week_is_five_working_days(self):
        self.assertEqual(working_days(self.monday, self.sunday), 5)

    def test_holiday_is_excluded(self):
        Holiday.objects.create(date=self.monday + timedelta(days=1), name="holiday")
        self.assertEqual(working_days(self.monday, self.sunday), 4)
```

**Run**
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py test
```

**Done when:** a full week counts 5, a holiday drops it to 4, both tests pass.
> `add holidays and working-day counter`

---

## Phase 4 — auth

**Goal:** users can register and exchange username/password for a JWT.

**File: `leave/serializers.py`** (new)
```python
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ("id", "username", "email", "password")

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
```

**File: `leave/views.py`** (replace the file)
```python
from rest_framework import generics, permissions

from .serializers import RegisterSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
```

**File: `leavehub/urls.py`** (replace the file)
```python
from django.contrib import admin
from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from leave.views import RegisterView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/register/", RegisterView.as_view()),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
]
```

**Verify (manual):**
```bash
curl -s -X POST localhost:8000/api/auth/register/ -d 'username=joe&password=secret123'
curl -s -X POST localhost:8000/api/auth/token/ -d 'username=joe&password=secret123'
# -> {"refresh":"...","access":"..."}
```

### Tests
**File: `leave/tests/test_auth.py`** (new)
```python
from rest_framework.test import APITestCase


class AuthTests(APITestCase):
    def test_register_then_get_token(self):
        r = self.client.post(
            "/api/auth/register/", {"username": "joe", "password": "secret123"}
        )
        self.assertEqual(r.status_code, 201)
        r = self.client.post(
            "/api/auth/token/", {"username": "joe", "password": "secret123"}
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)
```

**Run**
```bash
python manage.py test
```

**Done when:** register returns 201, token returns access + refresh, test passes.
> `wire up jwt auth and registration`

---

## Phase 5 — leave request + validation

**Goal:** an employee creates a leave request; the server computes `days`, validates it
(dates, balance, overlap), and reserves the days against `pending` — all safely.

**Why now:** this is the entry point to the workflow. Transitions in Phase 6 act on what this
creates.

**File: `leave/models.py`** (add)
```python
class LeaveRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    employee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="leave_requests"
    )
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.DecimalField(max_digits=5, decimal_places=2)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    approver = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="leave_decisions",
    )
    decision_note = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

**File: `leave/permissions.py`** (new)
```python
def role(user):
    return getattr(getattr(user, "profile", None), "role", None)
```

**File: `leave/serializers.py`** (add below `RegisterSerializer`)
```python
from datetime import date

from .calendar import working_days
from .models import LeaveBalance, LeaveRequest


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = ("employee", "days", "status", "approver", "decided_at")

    def validate(self, data):
        if data["start_date"] > data["end_date"]:
            raise serializers.ValidationError("start must be before end")
        if data["start_date"] < date.today():
            raise serializers.ValidationError("cannot request leave in the past")

        days = working_days(data["start_date"], data["end_date"])
        if days <= 0:
            raise serializers.ValidationError("no working days in that range")

        employee = self.context["request"].user
        try:
            balance = LeaveBalance.objects.get(
                employee=employee, leave_type=data["leave_type"],
                year=data["start_date"].year,
            )
        except LeaveBalance.DoesNotExist:
            raise serializers.ValidationError("no balance for that leave type/year")
        if balance.remaining < days:
            raise serializers.ValidationError("not enough balance")

        overlap = LeaveRequest.objects.filter(
            employee=employee, status__in=["pending", "approved"],
            start_date__lte=data["end_date"], end_date__gte=data["start_date"],
        ).exists()
        if overlap:
            raise serializers.ValidationError("overlaps an existing request")

        data["days"] = days
        return data
```

> Note: `year` is taken from `start_date.year`. A request that spans New Year is charged
> entirely to the start year — a known simplification; reject cross-year ranges later if you
> want.

**File: `leave/views.py`** (replace the file)
```python
from django.db import transaction
from rest_framework import generics, mixins, permissions, viewsets
from rest_framework.exceptions import ValidationError

from .models import LeaveBalance, LeaveRequest
from .permissions import role
from .serializers import LeaveRequestSerializer, RegisterSerializer


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


# create / list / retrieve only — a request changes via the approve/reject/cancel actions
# (Phase 6), never a plain PATCH/PUT/DELETE that would bypass the balance math.
class LeaveRequestViewSet(mixins.CreateModelMixin, mixins.RetrieveModelMixin,
                          mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = LeaveRequestSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        r = role(user)
        if r == "hr":
            return LeaveRequest.objects.all()
        if r == "manager":
            return LeaveRequest.objects.filter(employee__profile__manager=user)
        return LeaveRequest.objects.filter(employee=user)

    def perform_create(self, serializer):
        with transaction.atomic():
            req = serializer.save(employee=self.request.user)
            balance = LeaveBalance.objects.select_for_update().get(
                employee=req.employee, leave_type=req.leave_type, year=req.start_date.year
            )
            # Re-check under the row lock. validate() read the balance without one, so two
            # concurrent requests could both pass; this closes that race (atomic rolls back).
            if balance.remaining < req.days:
                raise ValidationError("not enough balance")
            balance.pending += req.days
            balance.save()
```

**File: `leavehub/urls.py`** (replace the file)
```python
from django.contrib import admin
from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from leave.views import LeaveRequestViewSet, RegisterView

router = DefaultRouter()
router.register("leave-requests", LeaveRequestViewSet, basename="leave-request")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/register/", RegisterView.as_view()),
    path("api/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/", include(router.urls)),
]
```

**Migration:** adds `leave_leaverequest`.

**Seed + verify (manual):** a request needs a `LeaveType` and a `LeaveBalance` for the user.
Seed them in the shell, then create a request over a future Mon–Fri:
```bash
python manage.py shell -c "
from datetime import date, timedelta
from django.contrib.auth import get_user_model
from leave.models import LeaveType, LeaveBalance
u = get_user_model().objects.get(username='joe')
lt = LeaveType.objects.create(name='annual', default_allocation_days=20)
LeaveBalance.objects.create(employee=u, leave_type=lt, year=date.today().year, accrued=20)
print('leave_type id', lt.id)"
```
```bash
curl -s -X POST localhost:8000/api/leave-requests/ -H "Authorization: Bearer $TOKEN" \
  -d 'leave_type=1&start_date=2026-07-06&end_date=2026-07-10'
# -> 201 with days=5; a second overlapping request -> 400 "overlaps an existing request"
```

### Tests
**File: `leave/tests/test_validation.py`** (new)
```python
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from leave.models import LeaveBalance, LeaveType

User = get_user_model()


class ValidationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("e", password="x")
        self.lt = LeaveType.objects.create(name="annual", default_allocation_days=20)
        self.start = date.today() + timedelta(days=7)
        while self.start.weekday() != 0:          # a future Monday
            self.start += timedelta(days=1)
        self.end = self.start + timedelta(days=4)  # Mon-Fri = 5 working days
        self.client.force_authenticate(self.user)

    def post(self):
        return self.client.post("/api/leave-requests/", {
            "leave_type": self.lt.id, "start_date": self.start, "end_date": self.end,
        })

    def test_insufficient_balance_is_rejected(self):
        LeaveBalance.objects.create(
            employee=self.user, leave_type=self.lt, year=self.start.year, accrued=2
        )
        self.assertEqual(self.post().status_code, 400)

    def test_valid_request_reserves_pending(self):
        LeaveBalance.objects.create(
            employee=self.user, leave_type=self.lt, year=self.start.year, accrued=20
        )
        self.assertEqual(self.post().status_code, 201)
        bal = LeaveBalance.objects.get(
            employee=self.user, leave_type=self.lt, year=self.start.year
        )
        self.assertEqual(bal.pending, 5)
```

**Run**
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py test
```

**Done when:** a valid request is 201 and reserves `pending`; insufficient balance, overlap,
and past dates are each 400; tests pass.
> `leave request create with balance and overlap validation`

---

## Phase 6 — state machine + balance effects

**Goal:** approve / reject / cancel a request, each adjusting the balance in the same locked
transaction so the numbers can't drift or be double-spent.

**File: `leave/models.py`** — add these imports at the top (merge with the existing
`from django.db import models` line):
```python
from django.db import models, transaction
from django.utils import timezone
```

Add the error (module level) and the transition methods inside the `LeaveRequest` class:
```python
class TransitionError(Exception):
    pass
```
```python
    def _balance(self):
        return LeaveBalance.objects.select_for_update().get(
            employee=self.employee, leave_type=self.leave_type, year=self.start_date.year
        )

    def approve(self, actor):
        if self.status != "pending":
            raise TransitionError("only pending requests can be approved")
        with transaction.atomic():
            bal = self._balance()
            bal.pending -= self.days
            bal.used += self.days
            bal.save()
            self.status = "approved"
            self.approver = actor
            self.decided_at = timezone.now()
            self.save()

    def reject(self, actor, note=""):
        if self.status != "pending":
            raise TransitionError("only pending requests can be rejected")
        with transaction.atomic():
            bal = self._balance()
            bal.pending -= self.days
            bal.save()
            self.status = "rejected"
            self.approver = actor
            self.decision_note = note
            self.decided_at = timezone.now()
            self.save()

    def cancel(self):
        if self.status not in ("pending", "approved"):
            raise TransitionError("cannot cancel this request")
        with transaction.atomic():
            bal = self._balance()
            if self.status == "approved":
                bal.used -= self.days
            else:
                bal.pending -= self.days
            bal.save()
            self.status = "cancelled"
            self.save()
```

**File: `leave/views.py`** — add imports and actions to `LeaveRequestViewSet`:
```python
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import LeaveBalance, LeaveRequest, TransitionError
```
```python
    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        req = self.get_object()
        if role(request.user) not in ("manager", "hr"):
            return Response({"detail": "not allowed"}, status=403)
        try:
            req.approve(actor=request.user)
        except TransitionError as e:
            return Response({"detail": str(e)}, status=400)
        return Response(LeaveRequestSerializer(req).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        req = self.get_object()
        if role(request.user) not in ("manager", "hr"):
            return Response({"detail": "not allowed"}, status=403)
        try:
            req.reject(actor=request.user, note=request.data.get("note", ""))
        except TransitionError as e:
            return Response({"detail": str(e)}, status=400)
        return Response(LeaveRequestSerializer(req).data)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        req = self.get_object()
        # only the owner or HR may cancel (a manager can see it but shouldn't withdraw it)
        if req.employee_id != request.user.id and role(request.user) != "hr":
            return Response({"detail": "not allowed"}, status=403)
        try:
            req.cancel()
        except TransitionError as e:
            return Response({"detail": str(e)}, status=400)
        return Response(LeaveRequestSerializer(req).data)
```

**Seed + verify (manual):** approving needs a manager who is the employee's `manager`:
```bash
python manage.py shell -c "
from django.contrib.auth import get_user_model
U = get_user_model()
emp = U.objects.get(username='joe')
mgr = U.objects.create_user('boss', password='secret123')
mgr.profile.role = 'manager'; mgr.profile.save()
emp.profile.manager = mgr; emp.profile.save()
print('manager set')"
```
Get a token for `boss`, then approve joe's pending request (id 1) and check the balance moved
from `pending` to `used`:
```bash
curl -s -X POST localhost:8000/api/leave-requests/1/approve/ -H "Authorization: Bearer $BOSS_TOKEN"
curl -s localhost:8000/api/me/balances/ -H "Authorization: Bearer $TOKEN"   # after Phase 7
```

### Tests
**File: `leave/tests/test_transitions.py`** (new)
```python
from datetime import date, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from leave.models import LeaveBalance, LeaveRequest, LeaveType, TransitionError

User = get_user_model()


class TransitionTests(TestCase):
    def setUp(self):
        self.employee = User.objects.create_user("emp", password="x")
        self.manager = User.objects.create_user("mgr", password="x")
        self.lt = LeaveType.objects.create(name="annual", default_allocation_days=20)
        self.bal = LeaveBalance.objects.create(
            employee=self.employee, leave_type=self.lt, year=date.today().year,
            accrued=20, pending=2,
        )
        self.req = LeaveRequest.objects.create(
            employee=self.employee, leave_type=self.lt,
            start_date=date.today() + timedelta(days=3),
            end_date=date.today() + timedelta(days=4),
            days=2, status="pending",
        )

    def test_approve_moves_pending_to_used(self):
        self.req.approve(actor=self.manager)
        self.bal.refresh_from_db()
        self.assertEqual(self.bal.used, 2)
        self.assertEqual(self.bal.pending, 0)

    def test_reject_releases_pending(self):
        self.req.reject(actor=self.manager, note="no")
        self.bal.refresh_from_db()
        self.assertEqual(self.bal.pending, 0)
        self.assertEqual(self.bal.used, 0)

    def test_cancel_approved_restores_used(self):
        self.req.approve(actor=self.manager)
        self.req.cancel()
        self.bal.refresh_from_db()
        self.assertEqual(self.bal.used, 0)

    def test_cannot_approve_twice(self):
        self.req.approve(actor=self.manager)
        with self.assertRaises(TransitionError):
            self.req.approve(actor=self.manager)
```

**Run**
```bash
python manage.py test
```

**Done when:** each transition moves the balance correctly, illegal moves raise, and approve/
reject are blocked for non-managers (verified in the API tests in Phase 10).
> `approve/reject/cancel with locked balance updates`

---

## Phase 7 — balances and calendar

**Goal:** an employee can see their balances, the team can see who's approved-off on a shared
calendar, and HR can manage leave types over the API.

**File: `leave/serializers.py`** (add)
```python
class LeaveBalanceSerializer(serializers.ModelSerializer):
    remaining = serializers.ReadOnlyField()

    class Meta:
        model = LeaveBalance
        fields = (
            "id", "leave_type", "year",
            "accrued", "used", "pending", "carried_over", "remaining",
        )


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = "__all__"
```
(`LeaveType` is already imported in `serializers.py` from Phase 5's `from .models import ...`.)

**File: `leave/permissions.py`** (add) — HR may write leave types; everyone authenticated reads:
```python
from rest_framework import permissions


class IsHROrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)
        return role(request.user) == "hr"
```
(`role` is already defined in `leave/permissions.py` from Phase 5.)

**File: `leave/views.py`** (add; also add `LeaveBalanceSerializer` and `LeaveTypeSerializer` to
the `.serializers` import, `IsHROrReadOnly` to the `.permissions` import, and `LeaveType` to the
`.models` import)
```python
class MyBalancesView(generics.ListAPIView):
    serializer_class = LeaveBalanceSerializer

    def get_queryset(self):
        return LeaveBalance.objects.filter(employee=self.request.user)


class CalendarView(generics.ListAPIView):
    serializer_class = LeaveRequestSerializer

    def get_queryset(self):
        qs = LeaveRequest.objects.filter(status="approved")
        start = self.request.query_params.get("from")
        end = self.request.query_params.get("to")
        if start and end:
            qs = qs.filter(start_date__lte=end, end_date__gte=start)
        if role(self.request.user) == "hr":
            return qs
        team = self.request.user.profile.team
        if not team:
            return qs.none()              # no team set -> show nothing rather than everyone
        return qs.filter(employee__profile__team=team)


class LeaveTypeViewSet(viewsets.ModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer
    permission_classes = [IsHROrReadOnly]
```
> The `if not team` guard matters: filtering on `team=""` would otherwise match every user
> who also has a blank team and leak their leave. Set a `team` on profiles for the calendar
> to be useful.

**File: `leavehub/urls.py`** — register the leave-types viewset on the existing router and add
the two list routes:
```python
from leave.views import (
    CalendarView, LeaveRequestViewSet, LeaveTypeViewSet, MyBalancesView, RegisterView,
)

router.register("leave-types", LeaveTypeViewSet, basename="leave-type")
```
```python
    path("api/me/balances/", MyBalancesView.as_view()),
    path("api/calendar/", CalendarView.as_view()),
```

**Verify (manual):**
```bash
curl -s localhost:8000/api/me/balances/ -H "Authorization: Bearer $TOKEN"
curl -s "localhost:8000/api/calendar/?from=2026-07-01&to=2026-07-31" -H "Authorization: Bearer $TOKEN"
curl -s localhost:8000/api/leave-types/ -H "Authorization: Bearer $TOKEN"     # any user can list
# creating a type requires hr (set a user's profile.role='hr' first):
curl -s -X POST localhost:8000/api/leave-types/ -H "Authorization: Bearer $HR_TOKEN" \
  -d 'name=sick&default_allocation_days=10'
```

### Tests
**File: `leave/tests/test_leave_types.py`** (new)
```python
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()


class LeaveTypeAccessTests(APITestCase):
    def test_employee_can_list_but_not_create(self):
        user = User.objects.create_user("e", password="x")   # role defaults to employee
        self.client.force_authenticate(user)
        self.assertEqual(self.client.get("/api/leave-types/").status_code, 200)
        r = self.client.post("/api/leave-types/", {"name": "sick", "default_allocation_days": "10"})
        self.assertEqual(r.status_code, 403)

    def test_hr_can_create(self):
        hr = User.objects.create_user("hr", password="x")
        hr.profile.role = "hr"
        hr.profile.save()
        self.client.force_authenticate(hr)
        r = self.client.post("/api/leave-types/", {"name": "sick", "default_allocation_days": "10"})
        self.assertEqual(r.status_code, 201)
```

**File: `leave/tests/test_balances_api.py`** (new)
```python
from datetime import date

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from leave.models import LeaveBalance, LeaveType

User = get_user_model()


class BalancesEndpointTests(APITestCase):
    def test_lists_my_balances_with_remaining(self):
        user = User.objects.create_user("e", password="x")
        lt = LeaveType.objects.create(name="annual", default_allocation_days=20)
        LeaveBalance.objects.create(
            employee=user, leave_type=lt, year=date.today().year, accrued=20
        )
        self.client.force_authenticate(user)
        r = self.client.get("/api/me/balances/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data), 1)
        self.assertEqual(float(r.data[0]["remaining"]), 20.0)   # number, not a string
```

**Run**
```bash
python manage.py test
```

**Done when:** balances list with a computed `remaining`, the calendar is team-scoped, tests
pass.
> `balances and team calendar endpoints`

---

## Phase 8 — accrual and carry-over

**Goal:** the two scheduled jobs that aren't request-driven — grant monthly accrual and roll
unused days into next year. No Celery here; they're management commands run by cron.

Create the commands package: `leave/management/__init__.py`,
`leave/management/commands/__init__.py` (both new, empty).

**File: `leave/management/commands/accrue_leave.py`** (new)
```python
from datetime import date

from django.core.management.base import BaseCommand

from leave.models import LeaveBalance


class Command(BaseCommand):
    help = "Add monthly accrual to active balances"

    def handle(self, *args, **options):
        year = date.today().year
        for bal in LeaveBalance.objects.filter(year=year).select_related("leave_type"):
            rate = bal.leave_type.accrual_per_month
            if not rate:
                continue
            cap = bal.leave_type.default_allocation_days
            bal.accrued = min(bal.accrued + rate, cap)
            bal.save()
        self.stdout.write("accrual done")
```

**File: `leave/management/commands/carry_over.py`** (new)
```python
from datetime import date

from django.core.management.base import BaseCommand

from leave.models import LeaveBalance


class Command(BaseCommand):
    help = "Roll remaining balance into next year"

    def handle(self, *args, **options):
        year = date.today().year
        for bal in LeaveBalance.objects.filter(year=year).select_related("leave_type"):
            lt = bal.leave_type
            carry = min(bal.remaining, lt.max_carry_over_days)
            starting = 0 if lt.accrual_per_month else lt.default_allocation_days
            LeaveBalance.objects.update_or_create(
                employee=bal.employee, leave_type=lt, year=year + 1,
                defaults={"carried_over": carry, "accrued": starting},
            )
        self.stdout.write("carry-over done")
```

**Verify (manual):**
```bash
python manage.py accrue_leave     # -> accrual done
python manage.py carry_over       # -> carry-over done
```

### Tests
**File: `leave/tests/test_commands.py`** (new)
```python
from datetime import date

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from leave.models import LeaveBalance, LeaveType

User = get_user_model()


class AccrualTests(TestCase):
    def test_accrual_adds_monthly_rate_up_to_cap(self):
        user = User.objects.create_user("e", password="x")
        lt = LeaveType.objects.create(
            name="annual", default_allocation_days=12, accrual_per_month=1
        )
        bal = LeaveBalance.objects.create(
            employee=user, leave_type=lt, year=date.today().year, accrued=0
        )
        call_command("accrue_leave")
        bal.refresh_from_db()
        self.assertEqual(bal.accrued, 1)
```

**Run**
```bash
python manage.py test
python manage.py accrue_leave
python manage.py carry_over
```

**Done when:** accrual adds the monthly rate up to the cap, carry-over opens next year's rows,
tests pass.
> `accrual and carry-over management commands`

---

## Phase 9 — API docs

**Goal:** a browsable OpenAPI schema and Swagger UI.

**File: `leavehub/urls.py`** — add the import and two routes:
```python
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
```
```python
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema")),
```

**Verify (manual):** open `http://localhost:8000/api/docs/`.

### Tests
**File: `leave/tests/test_schema.py`** (new)
```python
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

User = get_user_model()


class SchemaTests(APITestCase):
    def test_schema_endpoint_ok(self):
        self.client.force_authenticate(User.objects.create_user("s", password="x"))
        r = self.client.get("/api/schema/")
        self.assertEqual(r.status_code, 200)
```

**Run**
```bash
python manage.py test
```

**Done when:** `/api/docs/` renders and the schema test passes.
> `expose openapi schema and swagger ui`

---

## Phase 10 — fill the gaps

**Goal:** run the whole suite and add what you skipped at the endpoint level:
- overlap rejection and a past-dated request (400),
- cancelling an approved request restores `used` (you have the model test; add the API one),
- the manager-only guard on approve/reject (an employee hitting `approve` gets 403),
- the owner/HR-only guard on cancel.

Optional coverage:
```bash
pip install coverage
coverage run manage.py test && coverage report
```

**Done when:** the suite is green and each role/transition branch has a test.
> `round out test coverage`

---

## Phase 11 — polish

**Goal:** fill the README sections (Features, Tech Stack, Architecture, Running Locally,
Running Tests, API Endpoints), write `What I Learned` in your own words, and tidy serializer
docstrings so the schema reads cleanly.
> `flesh out readme and notes`

---

## Phase 12 — production hardening

**Goal:** the API behaves like a production service — versioned, paginated, throttled,
security-checked, deployable, with the accrual/carry-over jobs scheduled. Code and full detail
are in `ENGINEERING.md` §8–§10.

**Steps**
1. **Version the API** — mount the router under `api/v1/` (§8). Update test URLs to
   `/api/v1/...` (or use `reverse()`).
2. **Pagination + throttling** — add the `REST_FRAMEWORK` keys from §8, then fix the balances
   and calendar list tests to read `r.data["results"]`.
3. **Security** — add the hardening settings (§9) and get a clean
   `DJANGO_DEBUG=False python manage.py check --deploy`.
4. **Static + image** — WhiteNoise + `STATIC_ROOT`, add `gunicorn`/`whitenoise` to
   requirements and the `Dockerfile` (§10).
5. **Schedule the jobs** — register `accrue_leave` (monthly) and `carry_over` (year end) with
   cron or your platform's scheduler (§10).
6. **README** — Running Locally with `docker compose up` + migrate; add the CI badge.

**Verify**
```bash
ruff check . && ruff format --check .
DJANGO_DEBUG=False python manage.py check --deploy
coverage run manage.py test && coverage report
```

**Done when:** CI is green, `check --deploy` is clean, the API is under `/api/v1/` with
pagination + throttling, the scheduled jobs are registered, and `docker compose up` + gunicorn
serves it.
> `harden for production`

---

> Concurrency note: `select_for_update()` only takes a real row lock inside a transaction on
> Postgres — exactly this setup. That lock (in `perform_create` and every transition) is what
> stops two people spending the same last day at once.

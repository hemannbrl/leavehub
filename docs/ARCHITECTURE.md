# leavehub — architecture

Leave & attendance management API. Employees request time off, managers approve, HR
oversees policy. The deceptively tricky part is balance accounting and validation:
approving a request isn't flipping a status, it's doing math on a balance and rejecting
anything that doesn't add up.

## Roles

- **employee** — requests leave and sees their own balances and requests.
- **manager** — approves or denies their reports' requests; sees the team roster and calendar.
- **hr** — final oversight; manages leave types, allocations, balances, and holidays; sees
  everyone.

Identity comes from Django's `User`; the role is layered on via a `Profile` (OneToOne,
with a `role` choice).

## Data models

### Profile
- `user` — OneToOne to `User`
- `role` — choice: employee / manager / hr
- `manager` — FK User, nullable (who approves this employee's requests)
- `team` — char, optional (blank); drives the team calendar and roster

### LeaveType
- `name` — annual / sick / unpaid / etc.
- `default_allocation_days` — yearly allocation
- `accrual_per_month` — decimal, nullable (if the type accrues over the year)
- `paid` — bool
- `requires_approval` — bool
- `max_carry_over_days` — decimal (cap on what rolls into next year)

### LeaveBalance
- `employee` — FK User
- `leave_type` — FK LeaveType
- `year` — int
- `accrued` — decimal days granted so far this year
- `used` — decimal days on approved requests
- `pending` — decimal days reserved by pending requests
- `carried_over` — decimal from last year
- unique together (employee, leave_type, year)
- **remaining = accrued + carried_over - used - pending**

> `accrued/used/pending` are **stored counters**, mutated as requests move through their
> states — faster to read, but only safe if every change is atomic, which is why the
> transitions lock the row (see below). The alternative — deriving `used/pending` from
> request rows on the fly — can't drift but is heavier to query.

### LeaveRequest (aggregate)
- `employee` — FK User (PROTECT)
- `leave_type` — FK LeaveType
- `start_date`, `end_date`
- `days` — computed working days (excludes weekends and holidays)
- `reason` — text
- `status` — choice: pending / approved / rejected / cancelled
- `approver` — FK User, nullable (SET_NULL)
- `decision_note` — text, optional (blank)
- `decided_at` — nullable
- `created_at`, `updated_at`

### Holiday
- `date`, `name` — company holidays excluded from the working-day count

Modeling notes: use `DecimalField` for days to allow half-days. The working-day count
is the interesting bit — it walks the date range skipping weekends and `Holiday` rows.

## State machine and balance effects

```
            ┌──approve──> approved   (terminal)
pending ────┼──reject───> rejected   (terminal)
            └──cancel───> cancelled  (terminal)
```

| from | action | to | who | balance effect |
|------|--------|----|-----|----------------|
| (create) | submit | pending | owner | `pending += days` |
| pending | approve | approved | manager/HR — not the author | `pending -= days; used += days` |
| pending | reject | rejected | manager/HR — not the author | `pending -= days` |
| pending | cancel | cancelled | owner only | `pending -= days` |

Only `pending` requests move; `approved` / `rejected` / `cancelled` are terminal.

The balance effect is the whole point: it's tied to the transition and must stay
consistent with status. Transitions are methods on `LeaveRequest`
(`request.approve()`, etc.); each guards the current state and adjusts the balance
**in the same DB transaction**, with the balance row locked (`select_for_update`) so two
concurrent approvals can't both spend the last day.

**Authorization:** a manager acts only on their reports' requests; HR acts on anyone's.
Nobody may approve or reject their **own** request, so an HR's request is decided by
another HR. Cancelling is owner-only and only while pending — an approved request is
final and cannot be withdrawn.

### Validation on submit

This is where the bugs live, so it's the heart of the project:

- `start_date <= end_date` and not in the past
- computed `days > 0` after excluding weekends/holidays
- enough remaining balance for the leave type/year (`remaining >= days`)
- no overlap with the employee's existing pending/approved requests

## Accrual and carry-over

Days accrue over time and roll over year to year — both are scheduled, not request-time.
There's no Celery here, so run them as management commands on a schedule (cron):

- **accrual**: monthly, add `accrual_per_month` to each active `LeaveBalance.accrued`
  (capped at the type's yearly allocation).
- **carry-over**: at year rollover, move `min(remaining, max_carry_over_days)` into next
  year's `carried_over` and open fresh balance rows.

## Team calendar

`GET /api/v1/calendar/` returns approved leave over a date range, so people can see who's
out. **Managers and HR only** — a manager sees their team, HR sees everyone; employees
have no calendar access. Returns `{employee, leave_type, start_date, end_date, ...}` rows.

## API endpoints

The API is versioned under `/api/v1/`, paginated, and rate-limited.

```
POST   /api/v1/auth/register/                register a user
POST   /api/v1/auth/token/                   obtain JWT (+ /token/refresh/)

GET    /api/v1/me/                            current user: id, username, role, team
GET    /api/v1/me/balances/                   current user's balances
GET    /api/v1/employees/                     roster, scoped by role

GET    /api/v1/leave-types/                   list (HR creates/edits/deletes)

GET    /api/v1/calendar/                       team calendar (manager/HR, date-filtered)

GET    /api/v1/leave-requests/                list (own / reports' / all by role)
POST   /api/v1/leave-requests/                create (validates balance + overlap + dates)
GET    /api/v1/leave-requests/{id}/           retrieve

POST   /api/v1/leave-requests/{id}/approve/   -> approved  (manager/HR, not the author)
POST   /api/v1/leave-requests/{id}/reject/    -> rejected  (optional note)
POST   /api/v1/leave-requests/{id}/cancel/    -> cancelled (owner, pending only)

GET    /api/v1/schema/                         OpenAPI schema
GET    /api/v1/docs/                           Swagger UI
```

Transitions are separate action endpoints, not `PATCH status=...`. A minimal web client
(vanilla-JS SPA) is served at `/` and talks to this same API.

## Decisions made
- **Stored counters** (`accrued/used/pending`) with row-level locking, not derived-on-read
  — faster to read, kept correct by doing every change in one locked transaction.
- **Half-days** supported via `DecimalField`.
- **Approved leave is terminal** — it cannot be cancelled (only pending requests can).
- **Accrual** is monthly, capped at the type's allocation; **carry-over** is capped at
  `max_carry_over_days`.
- `requires_approval` exists on `LeaveType` but every request currently routes through
  approval; auto-approve is a future extension.

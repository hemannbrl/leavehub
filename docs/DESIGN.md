# leavehub — design

Leave & attendance management API. Employees request time off, managers approve, HR
oversees policy. The deceptively tricky part is balance accounting and validation:
approving a request isn't flipping a status, it's doing math on a balance and rejecting
anything that doesn't add up.

> Domain assumptions are marked with ">" — proposed defaults, change them before
> implementing.

## Roles

- **employee** — requests leave, sees their balance and the team calendar.
- **manager** — approves or denies their team's requests.
- **hr** — final oversight; manages leave types, allocations, balances, and holidays.

Identity from Django's `User`; role layered on via a `Profile` (OneToOne, `role`
choice), same as the other projects.

## Data models

### Profile
- `user` — OneToOne to `User`
- `role` — choice: employee / manager / hr
- `manager` — FK User, nullable (who approves this employee's requests)
- `team` — char or FK, nullable (drives the team calendar)

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

> The brief tracks accrued/used/remaining as stored counters, so the balance is
> mutated as requests move through their states. That's faster to read but easy to
> corrupt, so every change must be atomic (see below). The alternative — deriving
> used/pending from request rows on the fly — can't drift but is heavier to query.
> Pick one and note why.

### LeaveRequest (aggregate)
- `employee` — FK User (PROTECT)
- `leave_type` — FK LeaveType
- `start_date`, `end_date`
- `days` — computed working days (excludes weekends and holidays)
- `reason` — text
- `status` — choice: pending / approved / rejected / cancelled
- `approver` — FK User, nullable (SET_NULL)
- `decision_note` — text, nullable
- `decided_at` — nullable
- `created_at`, `updated_at`

### Holiday
- `date`, `name` — company holidays excluded from the working-day count

Modeling notes: use `DecimalField` for days to allow half-days. The working-day count
is the interesting bit — it walks the date range skipping weekends and `Holiday` rows.

## State machine and balance effects

```
pending ──approve──> approved
   │                    │
   ├──reject──> rejected│
   │                    └──cancel──> cancelled
   └──cancel──> cancelled
```

| from | action | to | who | balance effect |
|------|--------|----|-----|----------------|
| (create) | submit | pending | employee | `pending += days` |
| pending | approve | approved | manager | `pending -= days; used += days` |
| pending | reject | rejected | manager | `pending -= days` |
| pending | cancel | cancelled | employee | `pending -= days` |
| approved | cancel | cancelled | employee | `used -= days` |

The balance effect is the whole point: it's tied to the transition and must stay
consistent with status. Transitions are methods on `LeaveRequest`
(`request.approve()`, etc.); each guards the current state and adjusts the balance
**in the same DB transaction**, with the balance row locked (`select_for_update`) so two
concurrent approvals can't both spend the last day.

> Assumption: an approved request can still be cancelled, restoring `used`. You may
> restrict this to future-dated leave.

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

`GET /api/calendar/` returns approved leave for the requester's team over a date range,
so people can see who's out. Employees see their team; managers see their reports; HR
sees everyone. Returns `{employee, leave_type, start_date, end_date}` rows.

## API endpoints

```
POST   /api/auth/register/                register a user
POST   /api/auth/token/                   obtain JWT
POST   /api/auth/token/refresh/           refresh JWT

GET    /api/leave-types/                  list (hr creates/edits)
POST   /api/leave-types/                  create (hr)

GET    /api/me/balances/                  current user's balances
GET    /api/calendar/                     team calendar (date-range filtered)

GET    /api/leave-requests/               list (employee=own, manager=reports' queue)
POST   /api/leave-requests/               create (validates balance + overlap + dates)
GET    /api/leave-requests/{id}/          retrieve

POST   /api/leave-requests/{id}/approve/  -> approved
POST   /api/leave-requests/{id}/reject/   -> rejected (optional note)
POST   /api/leave-requests/{id}/cancel/   -> cancelled

GET    /api/schema/                       OpenAPI schema
GET    /api/docs/                         Swagger UI
```

Transitions are separate action endpoints, not `PATCH status=...`.

## Open decisions
- Stored counters vs derived used/pending (assumed stored, with locking).
- Half-day support (Decimal) vs whole days only.
- Whether approved leave can be cancelled, and any cutoff rule.
- Accrual cadence (monthly vs per-pay-period) and carry-over cap.
- Whether some leave types auto-approve (`requires_approval=False`).

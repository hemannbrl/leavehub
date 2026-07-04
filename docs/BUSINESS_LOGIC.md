# leavehub — business logic

The rules that act on the tables in `DATABASE.md`. The balance math is the whole point —
a status change here also moves numbers.

## Who can do what

| action                | employee | manager                | hr        |
|-----------------------|----------|------------------------|-----------|
| request leave         | own      | own                    | own       |
| see a request         | own      | their reports' + own   | all       |
| approve / reject      | no       | their reports' ¹       | anyone ¹  |
| cancel a request      | own ²    | own ²                  | own ²     |
| see own balances      | yes      | yes                    | yes       |
| team roster           | no       | their reports          | all       |
| team calendar         | no       | their team             | all       |
| manage types/holidays | no       | no                     | yes       |

¹ **Never your own request.** A manager/HR cannot approve or reject a request they
submitted; an HR's own request is therefore decided by *another* HR.
² **Owner-only, and only while `pending`.** Once a request is approved or rejected it is
final — nobody cancels it.

A manager's queue = requests whose `employee.profile.manager_id = me`, plus their own.

## What counts as a "day"

`days` = working days between `start_date` and `end_date` inclusive, **skipping weekends
and any date in `leave_holiday`**. A Mon–Fri request over a week with one holiday counts
4, not 5. This helper is used everywhere, so it's tested on its own first.

## Submitting a request (validation)

A new request is rejected unless **all** hold:
- `start_date <= end_date` and `start_date` is not in the past,
- computed `days > 0`,
- `remaining >= days` for that employee/type/year
  (`remaining = accrued + carried_over - used - pending`),
- no date overlap with the employee's existing `pending` or `approved` requests.

If it passes, the request is created `pending` and the days are reserved:
`pending += days`.

## Lifecycle and balance effects

Each transition changes `status` **and** the matching `leave_leavebalance`, in one DB
transaction, with the balance row locked (`SELECT ... FOR UPDATE`) so two managers
approving at once can't both spend the last day.

| from     | action  | to        | who       | balance effect                  |
|----------|---------|-----------|-----------|---------------------------------|
| (create) | submit  | pending   | owner     | `pending += days`               |
| pending  | approve | approved  | mgr/hr ¹  | `pending -= days; used += days` |
| pending  | reject  | rejected  | mgr/hr ¹  | `pending -= days`               |
| pending  | cancel  | cancelled | owner     | `pending -= days`               |

¹ Not the request's own author (see "Who can do what").

- Only `pending` requests transition. `approved`, `rejected`, and `cancelled` are all
  **terminal** — an approved request cannot be withdrawn.
- The reserve-on-submit / release-on-reject pattern is what stops people overbooking
  while requests await approval.

## Identity & roster endpoints

- `GET /api/v1/me/` returns the current user (`id, username, email, role, team`) so the
  client can shape the UI by role.
- `GET /api/v1/employees/` is the team roster, scoped by role: HR sees everyone, a manager
  sees their reports, an employee sees only themselves.

## Balances endpoint

`GET /api/v1/me/balances/` returns each `leave_leavebalance` row for the user with
`remaining` computed. It's a read of the same numbers the transitions maintain.

## Team calendar

`GET /api/v1/calendar/` returns **approved** requests over a date range
(`{employee, leave_type, start_date, end_date}`), for seeing who's out. **Managers and HR
only** — a manager sees their team, HR sees everyone; employees have no calendar access.

## Scheduled jobs (management commands, run by cron)

- **accrual** (monthly): `accrued += accrual_per_month`, capped at the type's
  `default_allocation_days`.
- **carry-over** (year rollover): open next year's balance rows and set
  `carried_over = min(remaining, max_carry_over_days)`.

No Celery here — these aren't request-driven, but they're periodic rather than real-time,
so a scheduled command is enough.

## Invariants worth protecting
- `remaining` is never negative — validation refuses requests that would cross zero.
- `pending` and `used` only change inside a transition, never by hand.
- An `approved` request is terminal: its days stay in `used` (it can't be cancelled back).
- Nobody approves or rejects their own request.
- Days are `numeric` so half-days are possible.

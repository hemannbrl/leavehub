# leavehub — database

Plain map of the tables. Django names them `<app>_<model>`; the app is `leave`.
`auth_user` is Django's built-in user table.

## Tables at a glance

```
auth_user (Django)
   │  1─1
leave_profile           role + who approves this person
   │
   │  employee / approver (FKs back to auth_user)
   ▼
leave_leaverequest ──*─1── leave_leavetype ──1─*── leave_leavebalance
                                                       (per employee, type, year)
leave_holiday  (dates excluded from day counts)
```

## leave_profile
| column     | type      | null | notes                                 |
|------------|-----------|------|---------------------------------------|
| id         | bigint PK | no   |                                       |
| user_id    | bigint FK | no   | → auth_user, unique                   |
| role       | varchar   | no   | employee / manager / hr               |
| manager_id | bigint FK | yes  | → auth_user; who approves their leave |
| team       | varchar   | yes  | drives the team calendar              |

## leave_leavetype
The policy for a kind of leave.

| column                 | type          | null | notes                            |
|------------------------|---------------|------|----------------------------------|
| id                     | bigint PK     | no   |                                  |
| name                   | varchar       | no   | annual / sick / unpaid…          |
| default_allocation_days| numeric(5,2)  | no   | yearly grant                     |
| accrual_per_month      | numeric(5,2)  | yes  | if it accrues over the year      |
| paid                   | boolean       | no   |                                  |
| requires_approval      | boolean       | no   | some types may auto-approve      |
| max_carry_over_days    | numeric(5,2)  | no   | cap rolled into next year        |

## leave_leavebalance
What each employee has, per leave type, per year. The number the whole app guards.

| column        | type         | null | notes                                  |
|---------------|--------------|------|----------------------------------------|
| id            | bigint PK    | no   |                                        |
| employee_id   | bigint FK    | no   | → auth_user                            |
| leave_type_id | bigint FK    | no   | → leave_leavetype                      |
| year          | integer      | no   |                                        |
| accrued       | numeric(5,2) | no   | granted so far this year               |
| used          | numeric(5,2) | no   | on approved requests                   |
| pending       | numeric(5,2) | no   | reserved by pending requests           |
| carried_over  | numeric(5,2) | no   | from last year                         |

Unique together: `(employee_id, leave_type_id, year)`.
`remaining` is not stored — it's `accrued + carried_over - used - pending`.

## leave_leaverequest
One request for time off.

| column        | type         | null | notes                                       |
|---------------|--------------|------|---------------------------------------------|
| id            | bigint PK    | no   |                                             |
| employee_id   | bigint FK    | no   | → auth_user (PROTECT)                        |
| leave_type_id | bigint FK    | no   | → leave_leavetype                            |
| start_date    | date         | no   |                                             |
| end_date      | date         | no   |                                             |
| days          | numeric(5,2) | no   | working days (weekends + holidays excluded) |
| reason        | text         | no   |                                             |
| status        | varchar      | no   | pending / approved / rejected / cancelled   |
| approver_id   | bigint FK    | yes  | → auth_user (SET NULL)                       |
| decision_note | text         | yes  |                                             |
| decided_at    | timestamptz  | yes  |                                             |
| created_at    | timestamptz  | no   | auto                                        |
| updated_at    | timestamptz  | no   | auto                                        |

Indexes: `(employee_id, status)`, and `start_date`/`end_date` for overlap and calendar
queries.

## leave_holiday
| column | type      | null | notes                  |
|--------|-----------|------|------------------------|
| id     | bigint PK | no   |                        |
| date   | date      | no   | unique                 |
| name   | varchar   | no   |                        |

## Delete rules
- `employee_id` uses PROTECT; `approver_id` / `manager_id` use SET NULL.
- A balance row is keyed to a real employee+type+year, so it isn't cascade-deleted by a
  request.

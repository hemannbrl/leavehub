# API reference

Base URL: `http://localhost:8000` in development. Interactive docs (Swagger UI) at
`/api/v1/docs/`, raw OpenAPI schema at `/api/v1/schema/`.

All endpoints except registration and token issuance require
`Authorization: Bearer <access>`.

## Authentication

```bash
# register (new users are employees; roles are elevated by HR/admin)
curl -X POST localhost:8000/api/v1/auth/register/ \
  -d 'username=evan&password=secret123'

# obtain a token pair
curl -X POST localhost:8000/api/v1/auth/token/ \
  -d 'username=evan&password=secret123'
# → 200 {"refresh":"…","access":"…"}

# refresh an expired access token
curl -X POST localhost:8000/api/v1/auth/token/refresh/ -d 'refresh=…'

# who am I
curl localhost:8000/api/v1/me/ -H "Authorization: Bearer $TOKEN"
# → {"id":3,"username":"evan","role":"employee","team":"Engineering"}
```

## Endpoints

```
POST   /api/v1/auth/register/                register a user
POST   /api/v1/auth/token/  (+ /refresh/)    obtain / refresh JWT

GET    /api/v1/me/                           current user (id, username, role, team)
GET    /api/v1/me/balances/                  current user's balances (accrued/used/pending/remaining)
GET    /api/v1/employees/                    roster — employee: self; manager: reports; HR: all

GET    /api/v1/leave-types/                  list; HR may create / edit / delete

GET    /api/v1/calendar/                     approved leave on a date range (manager/HR)
GET    /api/v1/leave-requests/               list — own / reports' / all by role
POST   /api/v1/leave-requests/               create (validated, see below)
GET    /api/v1/leave-requests/{id}/          retrieve

POST   /api/v1/leave-requests/{id}/approve/  -> approved  (manager/HR, never the author)
POST   /api/v1/leave-requests/{id}/reject/   -> rejected  (optional note)
POST   /api/v1/leave-requests/{id}/cancel/   -> cancelled (owner, pending only)

GET    /api/v1/schema/  ·  /api/v1/docs/     OpenAPI schema · Swagger UI
```

List responses are paginated: `{"count", "next", "previous", "results"}`, 20 per page.

## Creating a request

```bash
curl -X POST localhost:8000/api/v1/leave-requests/ -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"leave_type": 1, "start_date": "2026-08-03", "end_date": "2026-08-07", "reason": "family trip"}'
```

The server computes the working-day count (weekends and company holidays excluded) and
rejects, with a 400 and a field error: past start dates, ranges containing zero working
days, overlaps with the caller's existing pending/approved requests, and requests
exceeding the remaining balance. On success the days are reserved in the balance's
`pending` bucket.

## Decisions and errors

- **No self-approval** — approving or rejecting your own request returns 403, whatever
  your role. An HR's request is decided by another HR.
- **Managers decide only their reports'** requests (`employee.profile.manager = you`);
  HR decides anyone's.
- **Cancel** is owner-only and pending-only; decided requests are final (400).
- Approve moves the reserved days `pending → used`; reject/cancel release them. Each
  decision does its balance math inside one transaction with the balance row locked
  (`SELECT … FOR UPDATE`), so concurrent decisions can't double-spend a day.

## Rate limits

1000 requests/day per authenticated user; 20/hour anonymous. Exceeding them returns 429.

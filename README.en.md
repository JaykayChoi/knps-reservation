# Reservation Alert Monitor

This service checks KNPS campsites, Modu Parking monthly passes, and KTX seats, then sends Telegram alerts using per-monitor rules.

## Behavior

- A monitor has one category: `knps`, `moduparking`, or `ktx`.
- Category-specific filters live in one canonical `options` JSON object.
- Quiet hours are optional per monitor, disabled by default, and evaluated in Korea Standard Time.
- Identical upstream queries are cached within a check run.
- Available results are grouped into messages and split within Telegram limits.
- Only items in successfully delivered batches are written to cooldown history.
- KTX lookup is anonymous and directly uses the schedule contract used by Korail's official web ticket search.

## Layout

```text
backend/api/             Flask routes and legacy request adaptation
backend/domain/          Validation, time policy, and common models
backend/notifications/   Message formatting and Telegram transport
backend/providers/       KNPS, Modu Parking, and Korail clients
backend/repositories/    Supabase persistence
backend/services/        Check, notification, background job, and maintenance logic
frontend/js/             Dashboard API and station picker modules
supabase/migrations/     Schema history
scripts/                 Local migration test and opt-in manual tools
```

## Setup

Python 3.13+ and Node.js 18+ are required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m pip install pytest pytest-mock
npm ci
```

Configure these environment values locally or on Render:

```text
SUPABASE_URL=
SUPABASE_KEY=
KNPS_USERNAME=
KNPS_PASSWORD=
CHECK_PROBABILITY=0.2
```

KTX does not require a Korail ID or password. Telegram token and chat ID are stored per monitor.

### Local Docker KTX worker

Set production `SUPABASE_URL` and `SUPABASE_KEY` in `backend/.env`, then run
`docker compose up -d --build ktx-worker` from the repository root. No HTTP port
or domain is needed. The worker checks once on startup and draws a new 2–5 minute
delay after every completed check. Each run loads only active KTX monitors and
does not query Korail during a monitor's notification quiet hours. It shares
Supabase notification history and cooldowns with the main service. Use
`docker compose logs -f ktx-worker` to inspect it and
`docker compose stop ktx-worker` to stop it. Disable other scheduled KTX checks
to avoid duplicate provider requests.
The web service's scheduled `/api/check` runs KNPS and Modu Parking only. KTX
monitoring runs in the local Docker worker; the web KTX settings and manual
search remain available.

## Persistence

`monitor_settings` stores common fields, Telegram delivery details, cooldown, quiet hours, and category-specific `options`. `notification_history` uses generic `monitor_id`, `target_date`, `target_key`, `item_key`, and `is_waiting` keys for every category, including KTX. A zero cooldown and Test Now do not write history.

Example KTX options:

```json
{
  "departure": "서울",
  "arrival": "부산",
  "departure_code": "0001",
  "arrival_code": "0020",
  "date": "2026-10-01",
  "start_time": "08:00",
  "end_time": "18:00",
  "seat_classes": ["general", "special", "standing"]
}
```

## API

- `GET /api/health`
- `GET /api/settings/all`
- `GET /api/settings`
- `PUT /api/settings`
- `PUT /api/settings/{id}`
- `DELETE /api/settings/{id}`
- `DELETE /api/settings/{id}/history`
- `DELETE /api/history`
- `POST /api/check?test=true`, returning `202 queued` or `200 running`
- `GET /api/search`
- `GET /api/parking-lots`
- `GET /api/ktx/stations`

There is no `/api/ktx/status` endpoint or persisted KTX refresh status.

## Run and verify

```powershell
Set-Location backend
python app.py
```

```powershell
Set-Location backend
python -m pytest tests --ignore=tests/test_integration.py
python -m pytest tests/test_integration.py -k "not telegram_test_notification"
Set-Location ..
npx playwright test
.\scripts\test-local-migration.ps1
```

Run the opt-in live KNPS check with `python scripts/manual/check-knps.py 20261001` after configuring credentials. The live Telegram test remains opt-in.

## Migration

`20260922010000_generalize_monitors.sql` preserves existing IDs and data while renaming `user_settings` to `monitor_settings`, converting category-specific columns and `ktx_options` into `options`, and applying disabled quiet-hour defaults.

Before production, run `scripts/db/monitor_refactor_preflight.sql`, create a database backup, apply the migration, and run `monitor_refactor_verify.sql`. `monitor_refactor_rollback.sql` is the data-preserving rollback for the immediate deployment window.

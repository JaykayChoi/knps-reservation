# Category-specific reservation monitors

Each user_settings row has exactly one PostgreSQL enum category: knps,
moduparking, or ktx. Existing rows with parking lots are split into a KNPS
row and a parking row; MONTHLY history moves to the new parking row. Preserve
credentials, active state and cooldown. Migration must not discard settings
even if splitting exceeds the dashboard's normal ten-setting creation limit.

Retain existing KNPS columns and add ktx_options JSONB (departure, arrival,
date, start_time, end_time, seat_class). Clear unrelated filters on category
changes. API validates complete merged settings, including partial updates.
KTX monitors cover one date and an inclusive departure-time interval, general,
special or either class, for one adult. Multiple dates/routes use separate rows.

The modal offers three draggable category buttons and an accessible click/
keyboard alternative, with only relevant fields visible. Cooldown, active state,
name and Telegram configuration are shared. Dashboard cards show category details.

Use the pinned korail2 fork used by C:/work/korail_KTX_macro_telegrambot as a
dependency, not the reference project's reservation loop. Only search seats;
never reserve. KORAIL_ID and KORAIL_PASSWORD are server environment variables.
Create isolated, timeout-bounded sessions; paginate sold-out schedules as well
as available ones so later trains are not lost. Report failures distinctly.

On /api/check start at most one KTX background job per process. Return queued/
running status and expose last job status on GET /api/ktx/status. Existing
probability gating applies only to KNPS. KTX histories use date, route, train,
departure time and seat class; write only after successful Telegram delivery.

No Git mutations, live Telegram tests or production database changes. Verify
with mocked pytest and browser API interception. Keep Korean/English READMEs.

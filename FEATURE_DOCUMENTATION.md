# Feature Reference

## Monitors

Each monitor controls its category, category options, active state, cooldown, Telegram channel, and optional quiet hours. Quiet hours default to off with suggested times 23:00–07:00 KST.

KNPS options select a weekday or explicit date schedule, parks, facility types, and waiting-list alerts. Parking options select catalog lot IDs. KTX options select official stations, travel date, departure window, and any combination of general, special, and standing seats.

## Alerts

Results are combined into readable messages. KTX messages contain up to 20 items and KNPS or parking messages contain up to 30, with additional splitting when Telegram's text limit requires it. Cooldown history is scoped to the monitor and exact availability identity.

Suppressed quiet-hour results are not queued or written to history. A later run checks current availability again. Test Now follows quiet hours and bypasses cooldown history writes.

## KTX

Station names come from Korail's public station list and are selected through a searchable modal. Schedule lookup is anonymous; the service has no Korail credential environment variables and no refresh-status panel or endpoint.

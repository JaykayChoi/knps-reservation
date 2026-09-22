# System Architecture

Requests enter through the blueprints in `backend/api`. Routes validate and adapt request payloads, then call repositories or enqueue a check. Business rules do not live in `app.py`.

`CheckRunner` owns one lazily-created worker. `CheckService` loads active monitors, skips quiet monitors, builds category queries, and caches identical queries for one run. Providers return common `Availability` objects. `NotificationService` applies cooldowns, reloads the monitor immediately before every message, sends through `TelegramSender`, and records only successful batches.

Supabase access is limited to repositories. `monitor_settings.options` contains category filters; shared behavior remains in typed columns. `monitor_catalog` stores selectable parks, facility types, and parking lots. `notification_history` uses category-neutral identity fields.

External failures are raised and logged by type without exposing secrets. Empty inventory is a valid result; failed upstream requests are errors. Telegram POST requests are not retried automatically.

All persisted timestamps are UTC. Quiet hours and the daily reset window are interpreted in Asia/Seoul. Quiet intervals include the start and exclude the end, including intervals that cross midnight.

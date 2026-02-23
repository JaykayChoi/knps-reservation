# BACKEND KNOWLEDGE BASE

## OVERVIEW
Modular Python backend using Flask to serve settings and execute reservation checks.

## STRUCTURE
- `app.py`: Flask application. Provides endpoints for the frontend and triggers for cron jobs.
- `db.py`: Supabase client. Handles `user_settings` (singleton row) and `notification_history`.
- `scraper.py`: Stateless logic to fetch data from KNPS AJAX endpoints.
- `notifier.py`: Formats text and sends messages via Telegram Bot API.

## CONVENTIONS
- Use `requests` for API calls.
- Return consistent JSON error formats.
- Cooldown logic: `db.is_in_cooldown(identifier, days)` should be checked before sending any message.

## ANTI-PATTERNS
- **No Global State**: Keep scraping logic stateless. Pass settings into functions rather than reading them from disk inside modules.
- **Error Handling**: Every KNPS API call must be wrapped in a try-except block.

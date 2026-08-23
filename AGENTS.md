# KNPS Reservation Development Guide

This file is the repository-level instruction source for Codex. Claude Code may continue to use `.claude/`; keep both configurations unless the user explicitly asks for a migration or removal.

## Project Summary

KNPS Reservation monitors Korea National Park Service campsite availability and selected Modu Parking monthly passes, then sends Telegram notifications according to user-defined filters and cooldowns.

- Backend: Python, Flask, Supabase, Requests
- Frontend: vanilla JavaScript and Tailwind CSS in static HTML
- Notifications: Telegram Bot API
- Tests: pytest and Playwright

## Repository Map

- `backend/app.py`: Flask entry point, API routes, scheduled check orchestration
- `backend/db.py`: Supabase access, settings, status, and notification history
- `backend/scraper.py`: authenticated KNPS availability requests
- `backend/modu_scraper.py`: Modu Parking monthly-pass requests
- `backend/notifier.py`: Telegram message construction and delivery
- `backend/tests/`: pytest unit and route tests
- `frontend/index.html`: settings dashboard
- `frontend/search.html`: live availability search
- `tests/test_dashboard.spec.ts`: Playwright E2E test
- `supabase/migrations/`: database schema history
- `old/`: legacy reference; do not modify

For historical context, consult `.claude/memory/MEMORY.md` only when it is relevant. Follow links selectively. OMC state under `.omc/` is not a Codex dependency.

## Development Rules

- Keep backend behavior in the modular services under `backend/`; do not move active logic into monolithic or legacy files.
- Route persistent settings, status, and notification history through Supabase.
- Never hardcode the user's parks, facility types, parking lots, date ranges, credentials, or cooldowns. Read them from settings or environment configuration.
- Preserve cooldown behavior and per-setting notification history. Notification history keys use the target date plus facility identity; parking monthly passes use `MONTHLY` as the date key.
- Keep scraping functions stateless and pass settings explicitly. Avoid blocking the Flask request thread with new long-running work.
- Wrap external KNPS, Modu Parking, Supabase, and Telegram operations with appropriate error handling and logging. Do not silently turn failures into successful responses.
- KNPS responses may require EUC-KR or UTF-8 handling. Preserve explicit encoding behavior when changing the scraper.
- The frontend has no build step. Follow the existing vanilla JavaScript, static HTML, and Tailwind utility-class approach unless the user requests a framework migration.
- Add or update a Supabase migration when a persisted schema changes. Do not edit applied migrations merely to change an existing environment.
- Do not modify `old/` unless the user explicitly asks for legacy-code work.

## Security and External Side Effects

- Never hardcode, commit, or print tokens, passwords, chat IDs, Supabase keys, or other secrets. Local configuration files such as `config.ini`, `.env*`, and `backend/.env` are ignored and should only be inspected when the task explicitly requires it.
- Do not run `supabase db reset`, destructive SQL, or data-deleting API calls until the target is confirmed to be the local development environment.
- Do not run `test_api.py` as an automated test; it sends a real POST request to a running server.
- Do not use a bare `pytest` command from `backend/`. The top-level `backend/test_scraper_*.py` scripts perform live KNPS requests during collection.
- `backend/tests/test_integration.py::test_telegram_test_notification` may send a real Telegram message when credentials are loaded. Exclude it from normal verification unless the user explicitly wants the live integration tested.
- Playwright E2E tests require the Flask app and database and may create or edit settings. Run them only against a disposable/local environment.

## Setup and Verification

Use Python 3.13+ and Node.js 18+.

```powershell
# Python environment (from the repository root)
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend\requirements.txt
python -m pip install pytest pytest-mock

# JavaScript tooling
npm ci
```

Run the safe backend suite from `backend/`:

```powershell
python -m pytest tests --ignore=tests/test_integration.py
python -m pytest tests/test_integration.py -k "not telegram_test_notification"
```

Run the application:

```powershell
Set-Location backend
python app.py
```

Run E2E tests only after starting the application with a local/disposable Supabase database:

```powershell
npx playwright test
```

Choose verification proportional to the change. Backend behavior changes need relevant pytest coverage; frontend interaction changes need a targeted Playwright check when a safe local environment is available. Report any skipped live integration explicitly.

## Git Policy

- Perform no commit, push, branch, merge, rebase, reset, or other repository-changing Git operation unless the user explicitly requests it in text.
- Read-only Git inspection such as `git status`, `git diff`, and `git log` is allowed when relevant.
- This repository works directly on `master` and does not use pull requests. If the user explicitly asks to commit or push, do not create a feature branch or PR.
- When the user says `git에 올려줘`, commit the requested changes and push them; do not stop after the commit.

## Documentation

- Preserve the repository's existing README pair: `README.en.md` in English and `README.md` in Korean.
- Update documentation when an API contract, persisted setting, environment requirement, or operator workflow changes.

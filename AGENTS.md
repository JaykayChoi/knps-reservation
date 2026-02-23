# PROJECT KNOWLEDGE BASE: KNPS Reservation Auto-Notification System

**Generated:** 2026-02-23
**Core Stack:** Python (Flask), Supabase, Tailwind CSS, Telegram Bot API.

## OVERVIEW
A system to monitor Korea National Park Service (KNPS) campsite availability and send real-time Telegram notifications based on user-defined filters and cooldown periods.

## STRUCTURE
```
knps-reservation/
├── backend/          # Python/Flask API server & Core Logic
│   ├── app.py        # API Entry point & Router
│   ├── db.py         # Supabase interface (Settings & History)
│   ├── scraper.py    # KNPS API interaction logic
│   └── notifier.py   # Telegram notification service
├── frontend/         # Web-based settings dashboard
│   └── index.html    # Vanilla JS + Tailwind CSS UI
└── old/              # Legacy monolithic reference code (READ-ONLY)
```

## WHERE TO LOOK
| Task | Location | Notes |
|------|----------|-------|
| API Routes | `backend/app.py` | Handles settings sync and manual check triggers. |
| Scraping Logic | `backend/scraper.py` | Interacts with `selectCampRemainSiteList.do`. |
| DB Schema/Ops | `backend/db.py` | Manages Supabase CRUD and cooldown logic. |
| UI Components | `frontend/index.html` | Settings form and availability display. |

## CONVENTIONS
- **Backend**: Use modular services in `backend/`. Avoid monolithic scripts.
- **Database**: All persistence must go through Supabase. No local storage for core settings.
- **Filters**: NEVER hardcode park names or facility types. Always pull from DB settings.
- **Cooldown**: Respect the `cooldown_days` setting to prevent notification spam.

## GIT & RECORDING POLICY
- **Git Commit**: NEVER run `git commit` unless the user explicitly requests it.
- **Recording**: When the user says "record this" (기록해줘), you MUST update this `AGENTS.md` file (or relevant 지식 베이스 files) immediately to preserve context for future sessions.

## ANTI-PATTERNS
- **DO NOT** hardcode secrets (tokens, keys). Use environment variables.
- **DO NOT** modify files in `old/`. They are for reference only.
- **DO NOT** block the Flask main thread with long-running scrapes (use async or background triggers).

## COMMANDS
```bash
# Backend setup
cd backend
pip install -r requirements.txt
python app.py
```

## NOTES
- The KNPS API uses `EUC-KR` or `UTF-8` depending on the endpoint; ensure proper encoding in `scraper.py`.
- Notifications are keyed by `YYYYMMDD_ParkName_FacilityType` to track uniqueness.

## LOCAL DEVELOPMENT & TESTING
- **Local DB**: Supabase CLI is initialized and running via Docker (URL: http://127.0.0.1:54321).
- **Schema**: Tables `user_settings` and `notification_history` are synchronized with the PRD. ⚠️ `start_date` and `end_date` columns were added to support custom date ranges.
- **Testing**: ⚡ `pytest` is used for both unit and integration tests.
  - `backend/tests/test_db.py`: Unit tests for database operations using Mocks.
  - `backend/tests/test_scraper.py`: Unit tests for date calculation and API parsing logic.
  - `backend/tests/test_notifier.py`: Unit tests for Telegram message formatting.
  - `backend/tests/test_integration.py`: Integration tests verifying Flask endpoints and real Telegram notifications.
- **Security**: Local test credentials are stored in `config.ini` (ignored by git). DO NOT commit this file.
- **Debug**: Manual triggers (`POST /api/check`) prefix Telegram messages with `[TEST]` for clarity.


## SESSION ACCOMPLISHMENTS (2026-02-23)
 **Bug Fix**: Resolved 500 Internal Server Error by adding missing `start_date` and `end_date` columns to Supabase `user_settings` table.
 **Test Suite**: Implemented 20+ automated tests using `pytest` and `mocker` across all modules (`db.py`, `scraper.py`, `notifier.py`, `app.py`).
 **DevOps**: Integrated Supabase CLI for local Docker-based database development and schema migrations.
 **UI/UX**: Improved the Neobrutalist dashboard with better data persistence, "Select All" functionality, and manual test triggers with `[TEST]` prefix separation.
 **Security**: Secured test credentials in `config.ini` and updated `.gitignore` to exclude sensitive local files and `node_modules/`.
 **QA**: Created `QA_CHECKLIST.md` and verified all core system behaviors via Playwright E2E automation.
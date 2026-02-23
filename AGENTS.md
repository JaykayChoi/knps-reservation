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

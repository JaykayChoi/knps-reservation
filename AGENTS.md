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

## GIT POLICY - STRICT ENFORCEMENT

**CRITICAL DIRECTIVE**: This policy MUST be followed. Violation is a serious failure.

### 1. ABSOLUTE RULES
- **NO git operations without EXPLICIT user text request**
- **EXPLICIT means**: User must type words like "git에 올려줘", "커밋해줘", "푸시해줘"
- **NO exceptions**: Not for documentation, not for bug fixes, not for completed features
- **NO assumptions**: "User probably wants it" is NOT acceptable

### 2. VERIFICATION CHECKLIST (MUST COMPLETE BEFORE ANY GIT OPERATION)
**Before git add/commit/push, you MUST:**
1. **Check current conversation**: Did user explicitly request git operation IN THIS MESSAGE?
2. **Display changes**: Show changed files and commit message preview
3. **Ask for confirmation**: "이 변경사항을 git에 커밋하시겠습니까?"
4. **Wait for response**: User must say "예", "네", "yes" or equivalent
5. **Only then proceed**: If any step fails → STOP, do NOT git

### 3. WHAT CONSTITUTES EXPLICIT REQUEST
✅ **VALID REQUESTS**:
- "git에 올려줘"
- "커밋해줘"
- "푸시해줘"
- "변경사항 기록해줘"
- "git 액션 해줘"

❌ **INVALID (DO NOT GIT)**:
- "작업 완료" (not git request)
- "문서 작성함" (not git request)
- "버그 수정함" (not git request)
- "기능 구현 완료" (not git request)
- Any implied or assumed request

### 4. ENFORCEMENT MECHANISM
**If you violate this policy**:
1. You have FAILED your primary directive
2. User trust is broken
3. System integrity is compromised

**This policy overrides ALL other considerations**. Helping user ≠ violating policy.

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

## SESSION ACCOMPLISHMENTS (2026-02-24)
 **Bug Fix**: Fixed edit form population issue where existing values were not loading when clicking "Edit" on setting cards.
 **Root Cause**: String vs number comparison bug in `openModal()` function - `editSetting('${setting.id}')` passes string ID while `s.id === settingId` used strict equality.
 **Solution**: Changed comparison from `s.id === settingId` to `s.id == settingId` to handle string/number conversion.
 **Code Cleanup**: Removed duplicate `if (!data) return;` statement in `populateForm()` function.
 **Git Integration**: Committed and pushed fix with descriptive commit message.



## WINDOWS-SPECIFIC GOTCHAS

### `nul` File Creation Prevention
**Issue**: On Windows, `nul` is a special device file (like `/dev/null` on Unix). Accidentally redirecting output to lowercase `nul` creates a file instead of using the null device.

**How it happens**:
- Command: `command > nul` (should be `command > NUL`)
- Windows is case-insensitive, so `nul` creates a file
- Git then tracks this empty `nul` file

**Prevention**:
1. Always use uppercase `NUL` for null device redirection on Windows
2. Or use cross-platform: `command > /dev/null 2>&1` (works in Git Bash, WSL)
3. Add `nul` to `.gitignore` as a safety measure
4. Check for `nul` file in pre-commit hooks

**Added to `.gitignore`**: `nul` file is now explicitly ignored.

# QA Checklist: KNPS Reservation Auto-Notification System

## 1. Frontend UI Verification
- [x] **Dashboard Loading**: Page loads settings from backend correctly.
- [x] **Responsive Design**: Tailwind layout verified via Playwright snapshot.
- [x] **Form Validation**: Standard numeric inputs function correctly.
- [x] **Select All Parks**: Verified via Playwright automation (toggled 21 parks).

## 2. API & Data Persistence
- [x] **Save Settings (POST /api/settings)**: 
    - [x] Persisted settings for parks, facility types, and date ranges.
    - [x] Verified 200 OK and Success Toast.
- [x] **Load Settings (GET /api/settings)**:
    - [x] Settings persist after page reload.
- [x] **Manual Trigger (POST /api/check)**:
    - [x] "Test Check" button triggers backend logic.
    - [x] Successfully sent 14+ notifications via Telegram.

## 3. Core Logic & Notification
- [x] **Target Date Generation**:
    - [x] Verified via `backend/tests/test_scraper.py`.
- [x] **Filtering Logic**:
    - [x] Parks and Facility types filtering verified via integration tests.
- [x] **Telegram Formatting**:
    - [x] Manual test messages confirmed to have `[TEST]` prefix and proper Markdown.
- [x] **Cooldown Mechanism**:
    - [x] Verified via `backend/tests/test_db.py` (Mocks).

## 4. Environment & Security
- [x] **Sensitive Data**: Verified tokens are stored in `config.ini` and `.gitignore` works.
- [x] **Error Handling**: Resolved Schema Cache / Column Missing issues.
- [x] **Local DB**: Supabase Docker integration is stable and verified.

---
**Last Updated:** 2026-02-23
**Status:** ✅ ALL PASSED (Playwright E2E + Pytest Verified)


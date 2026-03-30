---
name: Session History
description: Past session accomplishments and key decisions for context continuity
type: project
---

## Session History (migrated from AGENTS.md, 2026-02-23 ~ 2026-02-26)

### 2026-02-23
- Bug Fix: Resolved 500 error by adding missing start_date/end_date columns to Supabase
- Test Suite: 20+ automated tests (pytest + mocker) across all modules
- DevOps: Supabase CLI integration for local Docker-based DB development
- UI/UX: Neobrutalist dashboard improvements, "Select All", manual test triggers
- Security: config.ini for test credentials, .gitignore updates
- QA: QA_CHECKLIST.md created, Playwright E2E automation

### 2026-02-24
- Bug Fix: Edit form population - string vs number comparison (=== to ==)
- DB Optimization: Simplified system_status schema, renamed last_check_time to last_check_at
- Auto-Maintenance: Notification history cleanup (7-day retention), last check time tracking
- All 34 tests passing after schema changes

### 2026-02-26
- New Feature: Waiting list notifications in scraper.py
- Notification Optimization: Telegram message chunking (30 items/message)
- Per-Setting History: Granular cooldowns per user setting
- DB Refactoring: Removed redundant identifier columns from notification_history
- New Feature: "Clear All History" button, DELETE /api/history endpoint
- Quick Search: Real-time availability search on separate page (search.html)
- UI Cleanup: Dashboard simplification, LINE#ID artifact removal

### 2026-03-30
- Migration: Moved from opencode (AGENTS.md) to Claude Code (.claude/CLAUDE.md)
- Memory: Established project-internal memory system in .claude/memory/

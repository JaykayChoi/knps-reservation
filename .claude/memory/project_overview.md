---
name: KNPS Reservation Project Overview
description: Core project context - Flask/Supabase/Telegram campsite monitoring system
type: project
---

KNPS Reservation Auto-Notification System monitors Korea National Park Service campsite availability and sends real-time Telegram notifications.

**Tech Stack:** Python Flask backend, Supabase (PostgreSQL), Vanilla JS + Tailwind CSS frontend, Telegram Bot API, Playwright E2E tests, pytest unit tests.

**Key Architecture:**
- Backend modules: app.py (routes), db.py (Supabase CRUD), scraper.py (KNPS API), notifier.py (Telegram)
- Frontend: index.html (dashboard), search.html (real-time search)
- Database: Supabase with 5 migrations, tables: user_settings, notification_history, system_status
- Deployment: Render (reverted), local dev via Supabase CLI + Docker

**Why:** User monitors KNPS campsite availability with customizable filters, date ranges, and cooldown periods for notifications.
**How to apply:** All backend work in modular services, no monolithic scripts. Filters from DB, never hardcoded.

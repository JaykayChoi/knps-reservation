# Categories and KTX Implementation Plan

Goal: Separate monitor categories and deliver KTX seat alerts.
Spec: ../specs/2026-09-21-categories-ktx-design.md
Architecture: Supabase enum and category-specific filters; stateless Korail
adapter and background notification worker; existing static dashboard.

Constraints: Python 3.13+, Node 18+, no Git mutations or live side effects.
User delegated database/implementation choices; execute inline.

- [x] Add settings validation tests, observe failure, implement settings_model.py
  and db.py normalization; return HTTP 400 on invalid settings.
- [x] Add forward SQL migration splitting mixed settings and moving MONTHLY
  history, with database category exclusivity checks.
- [x] Add mocked KTX pagination, failure, cooldown and dispatch tests; implement
  ktx_scraper.py, ktx_monitor.py, notifier.py and app.py integration.
- [x] Add category controls, conditional forms and cards in frontend/index.html;
  verify editing, switching categories and payloads using mocked Playwright.
- [x] Document migration and environment in both READMEs; run safe backend suite,
  inspect diff and audit all requirements.

Review focus: partial updates preserve category; switching clears stale filters;
pagination passes sold-out pages; errors never become empty success; cooldown
identity distinguishes route/train/class and history is written only on success.

## Verification ledger

- Category normalization RED (missing module), then GREEN.
- KTX adapter/monitor RED (missing module), then GREEN.
- Browser category selection RED (missing controls), then GREEN.
- Create payload and KNPS schedule validation RED, then GREEN.
- Korean message text and worker stale-status regression RED, then GREEN.
- Disposable PostgreSQL 17: applied legacy schema (update_schema before granular,
  matching their original dependency), fixture, new migration and assertions.
  Verified split rows, retained active/cooldown values, MONTHLY history relocation,
  retained KNPS history, enum/constraint and KTX status column. No production DB touched.
- Review: independent reviewer identified encoding corruption, invalid create
  payload handling, incomplete KNPS validation and stale worker-status race;
  all were reproduced and fixed with regression tests.
- Desktop browser rendered KTX modal inspected; category buttons support native
  keyboard click and drag/drop, irrelevant fields are hidden and disabled.
- Live Korail login/seat search and Telegram delivery intentionally not performed.
- Operational requirement: apply new migration and configure Korail credentials;
  single persistent worker process. No commit, push or branch operation performed.
- Final checks: 107 backend tests passed, 2 pre-existing dotenv tests skipped;
  1 non-sending integration test passed, live Telegram test deselected;
  3 intercepted Playwright tests passed; git diff --check clean.

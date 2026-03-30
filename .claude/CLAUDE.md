<!-- OMC:START -->
<!-- OMC:VERSION:4.9.3 -->

# oh-my-claudecode - Intelligent Multi-Agent Orchestration

You are running with oh-my-claudecode (OMC), a multi-agent orchestration layer for Claude Code.
Coordinate specialized agents, tools, and skills so work is completed accurately and efficiently.

<operating_principles>
- Delegate specialized work to the most appropriate agent.
- Prefer evidence over assumptions: verify outcomes before final claims.
- Choose the lightest-weight path that preserves quality.
- Consult official docs before implementing with SDKs/frameworks/APIs.
</operating_principles>

<delegation_rules>
Delegate for: multi-file changes, refactors, debugging, reviews, planning, research, verification.
Work directly for: trivial ops, small clarifications, single commands.
Route code to `executor` (use `model=opus` for complex work). Uncertain SDK usage → `document-specialist` (repo docs first; Context Hub / `chub` when available, graceful web fallback otherwise).
</delegation_rules>

<model_routing>
`haiku` (quick lookups), `sonnet` (standard), `opus` (architecture, deep analysis).
Direct writes OK for: `~/.claude/**`, `.omc/**`, `.claude/**`, `CLAUDE.md`.
</model_routing>

<skills>
Invoke via `/oh-my-claudecode:<name>`. Trigger patterns auto-detect keywords.
Tier-0 workflows include `autopilot`, `ultrawork`, `ralph`, `team`, and `ralplan`.
Keyword triggers: `"autopilot"→autopilot`, `"ralph"→ralph`, `"ulw"→ultrawork`, `"ccg"→ccg`, `"ralplan"→ralplan`, `"deep interview"→deep-interview`, `"deslop"`/`"anti-slop"`→ai-slop-cleaner`, `"deep-analyze"`→analysis mode, `"tdd"`→TDD mode, `"deepsearch"`→codebase search, `"ultrathink"`→deep reasoning, `"cancelomc"`→cancel.
Team orchestration is explicit via `/team`.
Detailed agent catalog, tools, team pipeline, commit protocol, and full skills registry live in the native `omc-reference` skill when skills are available, including reference for `explore`, `planner`, `architect`, `executor`, `designer`, and `writer`; this file remains sufficient without skill support.
</skills>

<verification>
Verify before claiming completion. Size appropriately: small→haiku, standard→sonnet, large/security→opus.
If verification fails, keep iterating.
</verification>

<execution_protocols>
Broad requests: explore first, then plan. 2+ independent tasks in parallel. `run_in_background` for builds/tests.
Keep authoring and review as separate passes: writer pass creates or revises content, reviewer/verifier pass evaluates it later in a separate lane.
Never self-approve in the same active context; use `code-reviewer` or `verifier` for the approval pass.
Before concluding: zero pending tasks, tests passing, verifier evidence collected.
</execution_protocols>

<hooks_and_context>
Hooks inject `<system-reminder>` tags. Key patterns: `hook success: Success` (proceed), `[MAGIC KEYWORD: ...]` (invoke skill), `The boulder never stops` (ralph/ultrawork active).
Persistence: `<remember>` (7 days), `<remember priority>` (permanent).
Kill switches: `DISABLE_OMC`, `OMC_SKIP_HOOKS` (comma-separated).
</hooks_and_context>

<cancellation>
`/oh-my-claudecode:cancel` ends execution modes. Cancel when done+verified or blocked. Don't cancel if work incomplete.
</cancellation>

<worktree_paths>
State: `.omc/state/`, `.omc/state/sessions/{sessionId}/`, `.omc/notepad.md`, `.omc/project-memory.json`, `.omc/plans/`, `.omc/research/`, `.omc/logs/`
</worktree_paths>

## Setup

Say "setup omc" or run `/oh-my-claudecode:omc-setup`.

<!-- OMC:END -->

---

# KNPS Reservation Auto-Notification System

**Core Stack:** Python (Flask), Supabase, Tailwind CSS, Telegram Bot API

## Overview
A system to monitor Korea National Park Service (KNPS) campsite availability and send real-time Telegram notifications based on user-defined filters and cooldown periods.

## Structure
```
knps-reservation/
├── .claude/              # Claude Code configuration & memory
│   ├── CLAUDE.md         # Project knowledge base (this file)
│   ├── memory/           # Project-internal memory system
│   ├── settings.json     # OMC plugin configuration
│   └── skills/           # OMC skills
├── backend/              # Python/Flask API server & Core Logic
│   ├── app.py            # API Entry point & Router
│   ├── db.py             # Supabase interface (Settings & History)
│   ├── scraper.py        # KNPS API interaction logic
│   ├── notifier.py       # Telegram notification service
│   ├── requirements.txt  # Python dependencies
│   └── tests/            # pytest unit tests
├── frontend/             # Web-based settings dashboard
│   ├── index.html        # Vanilla JS + Tailwind CSS UI (Main Dashboard)
│   └── search.html       # Real-time availability search page
├── supabase/             # Database config & migrations
│   ├── config.toml
│   └── migrations/       # SQL migration files
├── tests/                # E2E tests (Playwright)
│   └── test_dashboard.spec.ts
└── old/                  # Legacy monolithic reference code (READ-ONLY)
```

## Where to Look
| Task | Location | Notes |
|------|----------|-------|
| API Routes | `backend/app.py` | Settings sync and manual check triggers |
| Scraping Logic | `backend/scraper.py` | Interacts with `selectCampRemainSiteList.do` |
| DB Schema/Ops | `backend/db.py` | Supabase CRUD and cooldown logic |
| UI Components | `frontend/index.html` | Settings form and availability display |
| Search UI | `frontend/search.html` | Real-time availability search |
| E2E Tests | `tests/test_dashboard.spec.ts` | Playwright browser tests |
| DB Migrations | `supabase/migrations/` | Schema evolution history |

## Conventions
- **Backend**: Use modular services in `backend/`. Avoid monolithic scripts.
- **Database**: All persistence must go through Supabase. No local storage for core settings.
- **Filters**: NEVER hardcode park names or facility types. Always pull from DB settings.
- **Cooldown**: Respect the `cooldown_days` setting to prevent notification spam.
- **Frontend**: Use modern Tailwind utility classes. Sync state with backend immediately on "Save".
- **Error Handling**: Every KNPS API call must be wrapped in try-except.
- **No Global State**: Keep scraping logic stateless. Pass settings into functions.

## Anti-Patterns
- **DO NOT** hardcode secrets (tokens, keys). Use environment variables.
- **DO NOT** modify files in `old/`. They are for reference only.
- **DO NOT** block the Flask main thread with long-running scrapes.

## Commands
```bash
# Backend setup & run
cd backend
pip install -r requirements.txt
python app.py

# Run backend tests
cd backend && pytest

# Run E2E tests
npx playwright test
```

## Local Development & Testing
- **Local DB**: Supabase CLI via Docker (URL: http://127.0.0.1:54321)
- **Schema**: Tables `user_settings` and `notification_history`. `start_date` and `end_date` columns support custom date ranges.
- **Testing**: `pytest` for unit tests, Playwright for E2E.
- **Security**: Local test credentials in `config.ini` (git-ignored). DO NOT commit.
- **Debug**: Manual triggers (`POST /api/check`) prefix Telegram messages with `[TEST]`.

## Notes
- KNPS API uses `EUC-KR` or `UTF-8` depending on endpoint; ensure proper encoding in `scraper.py`.
- Notifications keyed by `YYYYMMDD_ParkName_FacilityType` for uniqueness.
- Telegram notifications split into chunks of 30 items for message size limits.

## Windows-Specific Gotchas
- Use uppercase `NUL` or cross-platform `/dev/null` for null device redirection.
- `nul` file is in `.gitignore` as safety measure.

---

## User Rules & Policies

### Memory Policy
- On session start, only auto-load `.claude/memory/MEMORY.md` index
- Read individual memory files only when relevant to the current task
- Do not load unnecessary documents for context efficiency

### Auto Team Composition
When receiving substantial work requests (code implementation, refactoring, debugging, review, etc.), assess the scale and nature of the work to automatically compose `/oh-my-claudecode:team`.

**Criteria:**
- **Direct handling**: Simple questions, config changes, memory management, minor edits to 1 file
- **Small team (2~3)**: 2~3 file edits, single feature implementation → primarily `executor`
- **Medium team (3~5)**: Multiple files, new feature development → `architect` + `executor` + `verifier` combo
- **Large team (5+)**: Architecture changes, large-scale refactoring → specialized agent pool per role
- **Debugging**: `debugger` + `tracer` combo
- **Code review**: `code-reviewer` + `security-reviewer` combo

Follow the user's explicit team composition if specified.

### Memory File Rules
- Do not create separate `feedback` type memory files
- Record feedback/rules directly in `CLAUDE.md`

### Git Rules
- When the user says "깃에 올려줘" (push to git), **always commit AND push** (not just commit)
- This project does **NOT use pull requests** and **always works on master branch**. Never create feature branches or PRs. Commit and push directly to master.

### GIT POLICY - STRICT ENFORCEMENT

**CRITICAL DIRECTIVE**: This policy MUST be followed. Violation is a serious failure.

- **NO git operations without EXPLICIT user text request**
- **EXPLICIT means**: User must type words like "git에 올려줘", "커밋해줘", "푸시해줘"
- **NO exceptions**: Not for documentation, not for bug fixes, not for completed features

### MD File Writing Rules
- All `.md` files written by Claude for record-keeping must be **written in English**
- When writing an English file, **always create a Korean translation** in the same folder as `filename.kr.md`
- `.kr.md` files are for user reference only; **Claude must NOT read `.kr.md` files** (excluded from reading targets)
- When **modifying or creating** a `.md` file, **always update/create the corresponding `.kr.md` file** as well

# CAOS Roadmap — Remaining Work

**Status:** Living backlog. Updated Apr 24, 2026 — evening.
**Context:** User is pausing active dev to daily-drive the app and surface real pain points before committing to the next wave.

Shipped so far (see `PRD.md` for details):
- Full UI layout fixes (drawer positioning, transparency, header spacing)
- Engine chips + LIVE web chip on assistant replies
- Aria web_fetch + github_fetch tools (SSRF-safe)
- Admin Dashboard with Base44 parity (6 tabs now: Stats, Spend, Errors, Timeline, Top Users, Usage)
- Per-engine spend tracking with USD cost + dynamic WCW meter
- Connectors framework + GitHub PAT UI
- Resend email for support tickets
- Error logging into `error_log` collection
- Ambient mode, scroll-step + bubble-opacity sliders
- Clickable WCW meter → opens Context Inspector
- L-tier connector blueprint at `/app/memory/CONNECTOR_BLUEPRINT.md`

---

## 🔥 High leverage (polish that makes CAOS feel done)

| # | Feature | Size | Notes |
|---|---|---|---|
| H1 | Budget alert (monthly $ cap + banner at 80 %/100 % + optional auto-switch to cheapest engine) | S | Uses existing Spend infra |
| H2 | Personal spend view in Profile drawer (already have `/usage/my-spend` API) | S | UI row + breakdown |
| H3 | Scrollbar styling pass across drawers + admin dashboard | XS | Dark-aesthetic match |
| H4 | "Sources used" tray per thread — collapsible footer listing every URL Aria fetched | S | Data already in messages.tools_used |
| H5 | Export thread as Markdown / PDF | S/M | Real archiving feature |
| H6 | `Cmd+K` command palette — search threads, switch engine, jump to settings | M | Leverage existing search infra |
| H7 | Global thread search (across all sessions, not just current) | S | Backend index exists |
| H8 | Syntax highlighting in code blocks | XS | Check Markdown renderer |
| H9 | Error detail drill-down — click Errors bar → see recent rows with stack traces | S | Data in error_log |

**Sub-total: ~80 credits**

---

## 🟡 Medium leverage (daily-driver features)

| # | Feature | Size | Notes |
|---|---|---|---|
| M1 | Thread pinning + folders (project grouping) | M | |
| M2 | "Fork this thread" — branch at any message | M | Clone session + link |
| M3 | Attachment gallery — grid view of uploaded files per thread | M | |
| M4 | Voice hands-free mode (push-to-talk + TTS only) | M | STT+TTS exist |
| M5 | Per-engine routing rules (Claude for code, Gemini for long docs, etc.) | M | |
| M6 | Shared thread links (read-only public URL) | M | New short-code system |
| M7 | Thread starring + `#tags` | S/M | Light organization |
| M8 | Message edit + regenerate | S | |
| M9 | Ambient mode scoped to thread (per-thread preference) | S | |
| M10 | Latency p50/p95 per engine in Admin | S | Data in engine_usage |
| M11 | Concurrent request queue chip ("processing 1 of 2") | S | |
| M12 | Welcome Tour 2.0 (explain Spend, Engine chips, GitHub connector, etc.) | S | |

**Sub-total: ~120 credits**

---

## 🟠 Platform muscle (architectural wins)

| # | Feature | Size | Notes |
|---|---|---|---|
| P1 | MCP client mode (universal connector protocol — replaces building bespoke connectors) | L | Replaces Gmail/Drive/Calendar grind if community has MCP servers for them |
| P2 | Multi-user shared thread (teammate joins same Aria session) | L | |
| P3 | Memory vault UI (explore/edit/delete what Aria remembers) | M | Memory exists, needs UI |
| P4 | Admin user management (impersonation, role edits, quota overrides) | M | |

**Sub-total: ~150 credits**

---

## 🟣 Infra / safety (ship before growth)

| # | Feature | Size | Notes |
|---|---|---|---|
| I1 | Fernet encryption at rest for connector tokens (multi-tenant readiness) | S | Already scaffolded |
| I2 | Rate-limit dashboard (who's hitting limits, adjust per-tier) | S | |
| I3 | Database backups to S3/R2 (scheduled CRON) | M | |
| I4 | Audit log (all admin actions recorded) | M | |
| I5 | Mobile PWA install (manifest + service worker) | M | |

**Sub-total: ~75 credits**

---

## 🟢 Growth / revenue (last, only with paying users waiting)

| # | Feature | Size | Notes |
|---|---|---|---|
| G1 | Stripe real billing tied to 6-tier quota | L | Test keys already in pod env |
| G2 | Referral program (credits for sign-ups) | M | |
| G3 | Public marketing landing page for caosos.com | M | Outside the app shell |
| G4 | Embeddable Aria widget (`<script>` drop-in) | L | |
| G5 | API access tier (developers call Aria via REST) | L | |

**Sub-total: ~255 credits**

---

## 🟠 Connectors (from `/app/memory/CONNECTOR_BLUEPRINT.md`)

| # | Feature | Size | Notes |
|---|---|---|---|
| C1 | Gmail Phase A — read inbox + thread summaries | L | OAuth + gmail.readonly scope |
| C2 | Gmail compose/send | M | Builds on C1 |
| C3 | Google Drive (read/search/attach) | L | drive.readonly |
| C4 | Google Calendar (read + create) | L | calendar.events |

**Sub-total: ~215 credits**

---

## 📊 Totals

| Bucket | Est. credits |
|---|---|
| 🔥 Polish (H1–H9) | 80 |
| 🟡 Medium (M1–M12) | 120 |
| 🟠 Platform (P1–P4) | 150 |
| 🟣 Infra (I1–I5) | 75 |
| 🟢 Growth (G1–G5) | 255 |
| 🟠 Connectors (C1–C4) | 215 |
| **EVERYTHING** | **~895** |
| + iteration buffer (~10 %) | **+90** |
| **Grand total** | **~985 credits** |

Current balance: **~697 credits** (as of this session end). Finishing the entire roadmap would require a top-up of ~300 credits.

---

## 🎯 Recommended paths (when user returns)

**Path A — Polish only (~80–100 credits)**: Ship H1–H9, call it done, collect user feedback. Leaves 500+ reserve.

**Path B — Polish + Gmail MVP (~250 credits)**: H1–H9 + C1 + C2. CAOS becomes your real inbox. Leaves 400+ reserve.

**Path C — Daily driver (~350 credits)**: Polish + select Medium items (M4 voice hands-free, M5 routing rules, M8 edit+regenerate, M12 welcome tour) + Gmail A. Full everyday experience.

**Path D — Platform-first (~400 credits)**: P1 MCP client (replaces most of C1–C4 grind) + polish bundle. Forward-looking bet.

**Path E — Full commercial (~985 credits, needs top-up)**: Everything. Ship-ready SaaS with billing, referrals, widget, and API.

---

## 📝 Notes for next agent

- User is **credit-sensitive**. NEVER use `testing_agent_v3_fork` unless explicitly requested. Use `mcp_screenshot_tool` + `curl` + `python -c` instead.
- User daily-drives CAOS on custom domain `caosos.com`. After every ship, remind them to click "Re-deploy changes" on the Emergent dashboard.
- Last working tech stack: React + FastAPI + MongoDB. Backend services modular; see `/app/backend/app/services/` and `/app/backend/app/routes/`.
- Active admin email for auth flows: check `/app/memory/test_credentials.md` + `ADMIN_EMAILS` in `app/services/auth_service.py`.
- When adding new connectors, ALWAYS call `integration_playbook_expert_v2` first — OAuth flows change constantly.

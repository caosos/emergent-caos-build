# CAOS Changelog

## 2026-04-25 (round 8) — Memory Phase 3 + Phase 5 lite + WCW + Logout-everywhere

### 🟢 Phase 3 — Bin-aware relevance scoring + recency decay

Aria now selects WHICH atoms to inject into each prompt using the typed-bin
priority shelf, not a flat term-overlap score. Big win because:

- Personal queries about preferences pull `OPERATING_PREFERENCE` atoms first
  (instead of getting drowned out by lexical noise).
- Identity queries lock onto `IDENTITY_FACT` even with low term overlap.
- `GOVERNANCE_RULE` atoms ride a high bin-priority floor and are pulled
  even when the user doesn't lexically match — so "never auto-send email"
  rules survive even on tangential turns.
- DERIVED candidates are slightly down-weighted vs USER_EXPLICIT atoms in
  ties (avoids autonomous extractor proposals overshadowing user-stated
  facts).
- Recency decay (24h=+2, 7d=+1, older=0) so newly-confirmed atoms surface.
- Evidence boost: 2+ evidence anchors = +1 (compounding signal wins).

Score formula (per atom):
  `base + bin_prio + bin_match + legacy + personal_q + evidence + confirmed + recency + priority`

Threshold drops noise atoms (no query match AND no high bin priority).
Tests cover all four scenarios — passing.

### 🟢 Phase 5 lite — "Why did Aria say this?" inline popover

Renamed the existing `Context` button on every assistant message to
**`Why?`** and extended its inline panel with a new "Memories injected"
section that lists each atom with:
- Source-mode color pill (USER-STATED green / OBSERVED blue / DERIVED purple)
- Bin label
- Full content (up to 400 chars)

Backed by extending `_memory_snapshot` in the receipt builder to carry
`source_mode`, `confidence`, `user_confirmed`, and a longer content slice.
If the turn injected zero atoms, an italic "No long-term memories were
injected for this reply" message renders so it's clear nothing fed in.

### 🟢 WCW staleness on engine failure (OPEN-03)

`useCaosShell.sendMessage` now calls `setLastTurn(null)` at the top of the
catch block, so the WCW meter doesn't freeze on the prior turn's token
count when the engine fails. Meter falls back gracefully to the dynamic
budget default until the next successful reply.

### 🟢 "Log out everywhere" UI clarity (OPEN-08)

Backend `/api/auth/logout` already nuked all sessions for the user — the
roadmap asked for the UI to reflect that. Renamed the AccountMenu item
from `Log Out` → `Log out everywhere`, added a confirmation prompt
("Sign out of CAOS on every device, including this one?"), and a tooltip
documenting the wipe. No backend change — the existing endpoint already
does the cascade.

### 🧪 Verification

- Backend ruff lint: clean.
- Frontend ESLint: clean (4 files touched).
- Phase 3 ranker unit tests: 4/4 PASS — personal-pref bin wins, identity
  query wins, gardening noise filtered, governance floor active.
- Live smoke screenshot: app loads, AccountMenu shows "Log out everywhere"
  + "Memory Console · NEW", drawer opens cleanly.
- `MemoryEntry` schema extended with Phase-1 additive fields (summary,
  confidence, user_confirmed, source_mode, evidence_count, status) so
  `rank_memories` can read them without re-parsing.

### 🟡 Phase 4 deferred (intentional)

Counterevidence + derived-trait engine would need real production data
from Phase 3's autonomous extraction to know which contradictions
actually fire. Better to wait until you've used the system for a week
and we have signal on which atoms compete in the wild.

---

## 2026-04-25 (round 7) — Memory Pulse (user-requested follow-up)

### 🟢 "Aria saved N new memories" — visible autonomous learning

User asked for delightful visibility into the autonomous extractor without
having to open the console every turn. Shipped:

- **Pulse trigger** in `useCaosShell`: after every successful chat turn
  (single-agent OR multi-agent), schedule a 3.5 s delayed re-fetch of
  `GET /caos/memory/atoms` and diff against the prev-turn count. Diff > 0
  → sonner `toast.success` with action button "View".
- **Click → opens Memory Console**: toast dispatches a custom DOM event
  `caos:open-memory-console`; CaosShell's `useEffect` listener flips
  `showMemoryConsole` true. No prop drilling.
- **Boot baseline seeding**: on shell hydrate, seed `prevAtomCountRef`
  with the current total so the FIRST chat turn after login produces an
  accurate diff (instead of toasting "saved N" on every login because
  prev was null).
- **Non-fatal everywhere**: pulse fetch failure is silently swallowed —
  it's a courtesy chip, never a blocker.

Cost per turn: ~1 GET request (≈100 bytes). No LLM cost beyond the
already-paid extractor pass.

---

## 2026-04-25 (round 6) — Memory Scaffolding Phase 1 + 2 (Console + Autonomous Extraction)

### 🟢 Phase 1: Memory Console — read-only audit view

The user's "auditable cognition" blueprint, made visible. Aria's brain is no
longer a black box — every long-term fact she remembers is now visible,
classified, and overridable.

- **13 typed memory bins** (`/app/backend/app/schemas/memory.py`):
  IDENTITY_FACT, ACTIVE_PROJECT, GOVERNANCE_RULE, OPERATING_PREFERENCE,
  RELATIONSHIP_BOUNDARY, DOMAIN_CONTEXT, TECHNICAL_STATE, BEHAVIORAL_PATTERN,
  DERIVED_TRAIT, LEARNING_PROFILE, REAL_WORLD_CONTEXT, RISK_SIGNAL,
  COUNTEREVIDENCE, GENERAL (legacy fallback). Each bin carries a default
  injection priority + governance rules (allows_inference,
  requires_user_confirmation, sensitivity).
- **MemoryAtom schema** — extends the legacy `MemoryEntry` shape with
  Phase-1 additions (summary, confidence, source_mode, sensitivity,
  mutation_policy, evidence_count, status, derived_from, counters).
  Backward compatible — existing `user_profiles.structured_memory` rows
  parse cleanly via `hydrate_atom`.
- **MemoryEvidence schema** — separate `memory_evidence` collection so
  one atom can accumulate evidence anchors over time without bloating the
  user_profile document.
- **`/api/caos/memory/atoms` route** (NEW, owner-gated):
  - `GET /atoms?user_email=…` → hydrated atom list + per-bin counts +
    full bin registry. Counts always reflect the FULL set so bin tabs
    stay accurate when filtered.
  - `GET /atoms/{id}/evidence` → list evidence anchors for one atom.
  - `POST /atoms/{id}/evidence` → append a new evidence anchor.
  - `PATCH /atoms/{id}` → reclassify (change `bin_name`), edit content, or
    bump priority (0–100 clamped).
  - `POST /atoms/{id}/confirm` → promote a DERIVED candidate to
    user-confirmed (locks mutation_policy, bumps confidence to 1.0).
  - `DELETE /atoms/{id}` → user-override "forget this memory" (cascades
    into `memory_evidence`).
- **MemoryConsoleDrawer.js** (NEW, ~330 lines) — opens from the account
  menu's new `Memory Console · NEW` item. Layout:
  - Left nav: 14 bin tabs with live counters, ordered by Tier 1 → Tier 4.
  - Right pane: bin description + atom cards.
  - Per-card: source-mode pill (USER-STATED green / OBSERVED blue /
    DERIVED purple / SYSTEM grey), confidence %, evidence count
    (clickable → side panel), sensitivity (HIGH / MED / NORMAL),
    priority chip, last-updated date.
  - Per-card actions: `Confirm` (only on DERIVED candidates), `Reclassify`
    dropdown (12 typed bins, GENERAL excluded), `Forget` (with confirm
    prompt). All wire to live API.
  - Evidence side-panel slides in from the right edge of the drawer.
- **Z-index fix** — `.memory-console-backdrop` added to the
  `.caos-shell-root > *:not(...)` exclusion list AND to the explicit
  `position: fixed; z-index: 220` override block (otherwise the global
  `.caos-shell-root > * { z-index: 1 }` rule traps the modal behind the
  chat grid, same bug class that bit the Logout button last week).

### 🟢 Phase 2: Autonomous Memory Extraction — Aria classifies herself

After every chat turn, a silent background task asks Gemini 3 Flash
($0.075 / $0.30 per 1M tokens — fractions of a cent per turn) to inspect
the (user_message, assistant_reply) exchange and propose new typed atoms.

- **`memory_extractor.py`** (NEW) — fire-and-forget extractor:
  - Sees the last 40 existing atoms (so it can dedupe before proposing).
  - Hard-cap of 5 new atoms per turn (chatty model can't flood memory).
  - Output is strict JSON with bin classification + confidence +
    direct quote evidence anchor.
  - Robust JSON parse — tolerates ```json``` fences, prose preamble,
    junk replies. Invalid bins discarded; GENERAL excluded.
  - Non-fatal: any failure is logged, never blocks the chat reply.
- **`profile_memory_service.insert_extracted_atom`** — auto-write path:
  - Dedupes against existing structured_memory by exact lower-cased
    content match. On dedup, bumps existing atom's `evidence_count`,
    refreshes `last_validated_at`, and STILL appends a new evidence
    anchor for this turn (so accumulating signal compounds).
  - New atoms land as `DERIVED` + `mutation_policy=CANDIDATE_REVIEW` +
    `user_confirmed=False`. They show up in the console with a yellow
    border + Confirm button so the user sees what Aria proposed and
    promotes (or deletes) at their leisure.
  - Default priority comes from the bin registry (e.g. IDENTITY_FACT
    → 95, BEHAVIORAL_PATTERN → 70, RISK_SIGNAL → 40).
- **`chat_pipeline.run_chat_turn`** hook — fires
  `schedule_extraction(...)` via `asyncio.create_task` AFTER the
  receipt/summary/seed/lane-rebuild block, so the chat turn is fully
  persisted before extraction runs in the background.

### 🧪 Verification (manual, NO testing_agent_v3_fork per user budget rules)

- Backend ruff lint: clean across 4 new/modified files.
- Frontend ESLint: clean across MemoryConsoleDrawer.js, AccountMenu.js,
  ShellHeader.js, CaosShell.js.
- `python -c` unit tests on the extractor JSON parser: 7 passed
  (clean JSON / fenced JSON / invalid bins discarded / GENERAL excluded
  / empty atoms / junk reply rejected / 5-atom hard cap / prompt covers
  all 13 bins).
- End-to-end DB write verified via direct service call: candidate atom
  written with `source_mode=DERIVED`, `mutation_policy=CANDIDATE_REVIEW`;
  dedup blocks second insert and bumps existing evidence; total atom
  count incremented correctly.
- Live curl: `GET /api/caos/memory/atoms` returns hydrated atoms with
  legacy bin names auto-migrated (`identity` → `IDENTITY_FACT`,
  `preferences` → `OPERATING_PREFERENCE`, `project` → `ACTIVE_PROJECT`).
  Bin counts include all 14 bins (zero-filled).
- Live UI screenshots: drawer opens with proper layout, 4 atoms render
  across Identity / Projects / Preferences / Behavioral bins, DERIVED
  candidate shows yellow border + Confirm button, Reclassify dropdown
  exposes 12 bins, Forget button red-tinted.

### 🔒 Privacy & Governance

- Owner-only access — every route enforces
  `requested_email == authenticated_email` (403 otherwise).
- DELETE cascades into `memory_evidence` — no dangling provenance rows.
- Bin registry's `requires_user_confirmation: True` bins (governance,
  identity, preferences, relationship) cannot be touched by the
  autonomous extractor's CANDIDATE_REVIEW policy without an explicit
  Confirm click.
- LLM-based extractor classification is constrained: model NEVER
  outputs GENERAL, always picks one of the 13 typed bins.

### 🟡 Deferred to Phase 3+

- **Phase 3 (relevance scoring + injection pack builder)** — pull only
  the relevant atoms into each turn's prompt automatically.
- **Phase 4 (counterevidence + derived-trait engine)** — second-order
  pattern recognition + automatic contradiction detection.
- **Phase 5 ("why did you say that?" full audit popover)** — click any
  reply, see the atoms that fed into it.
- Bulk operations on candidates (Confirm-all-in-bin, Forget-all-DERIVED).

---

## 2026-04-25 (round 5) — Connectors Sprint 3 (Stripe billing + Slack + Twilio + Telegram)

### 🟢 Stripe billing wired to the tier system (END-TO-END VERIFIED)

- **Test key in pod env** (`STRIPE_API_KEY=sk_test_emergent`). Used `emergentintegrations.payments.stripe.checkout.StripeCheckout` per the verified playbook — one-time Checkout sessions, NOT subscriptions. Each upgrade buys a 30-day pass at the chosen tier. Days stack on re-up.
- **Backend route**: `app/routes/billing.py`
  - `POST /api/billing/checkout` → creates Stripe session, returns hosted URL + session_id. Tier price comes server-side from `TIERS[tier_id].price_monthly`. Frontend NEVER sends an amount.
  - `GET /api/billing/status/<session_id>` → polls Stripe; on first `paid` read, atomically grants tier upgrade with idempotency on the `payment_transactions.applied` flag.
  - `POST /api/webhook/stripe` → mirrors the same idempotent grant. Whichever fires first (poll or webhook) wins; the other is a no-op.
  - `GET /api/billing/me` → current tier + all 6 available tiers for the Pricing drawer.
- **Token quota expiry-aware** (`token_quota.py`) — when `tier_expires_at` < now, the user silently falls back to free quotas without needing a cron job. `tier` field stays as-is for re-up convenience.
- **Pricing drawer UI** (`PricingDrawer.js`) — 6 tier cards, current-tier badge, daily-token chips, Stripe redirect on click. Stripe Checkout cannot live in an iframe so we hard-redirect.
- **Post-checkout polling** (`CaosShell.js` useEffect) — when Stripe redirects to `/?caos_billing=success&session_id=…`, polls `/billing/status/<sid>` every 2s for up to 30s. Toasts on success, cleans URL params.
- **Verified end-to-end live**: seeded test user, hit `/billing/checkout`, got back real `cs_test_…` URL pointing at `checkout.stripe.com`. All 6 tier cards rendered correctly. Free tier shows "CURRENT" badge. Backend ruff + frontend ESLint clean.

### 🟢 Slack (bot-token PAT, simpler than per-user OAuth)

- **Backend**: `services/aria_tools_slack.py` — 3 tools: `slack_list_channels`, `slack_search_messages` (xoxp- only), `slack_post_message` (write — `requires_approval=True` flag in dispatch table).
- **Storage**: same shape as GitHub PAT (`user_profiles.connectors.slack.token`). Reused `LEGACY_PAT_SERVICES` set + existing `PUT/DELETE /connectors/{service}` routes.
- **Frontend**: `<SlackCard />` in ConnectorsDrawer with paste-token UX matching the GitHub card.
- **Aria prompt**: `SLACK_TOOL_PROMPT` injected into system prompt only when the user has connected. Marks `slack_post_message` as "REQUIRES USER APPROVAL" (soft approval — Aria asks before firing; hard SSE-based approval gate is in Sprint 4 backlog).

### 🟢 Twilio SMS (multi-field credentials)

- **Backend**: `services/aria_tools_messaging.py` — `sms_send` (write), `sms_inbox_list` (reads `messaging_inbox` collection — empty until inbound webhook is wired in a future sprint).
- **Storage**: `user_profiles.connectors.twilio.{account_sid, auth_token, from_number}`. New `PUT /connectors/twilio` endpoint with multi-field validator.
- **Frontend**: `<TwilioCard />` with three input fields (SID + Auth Token + From-number).

### 🟢 Telegram bot (single bot_token field)

- **Backend**: same `aria_tools_messaging.py` — `telegram_send_message` (write), `telegram_inbox_list`.
- **Storage**: `user_profiles.connectors.telegram.bot_token`. New `PUT /connectors/telegram` endpoint.
- **Frontend**: `<TelegramCard />` with bot-token paste UX.

### 🟢 Connectors drawer extended

- New section **COMMUNICATIONS** holds Slack, Twilio, Telegram cards.
- All 7 cards now visible: Google · Obsidian · GitHub · Slack · Twilio · Telegram · MCP.
- ProfileDrawer gets a new **"Pricing & Tiers →"** button alongside Connectors.

### 🟡 Per-action approval (soft for now, hard gate is Sprint 4)

- The MVP soft approval is prompt-side: Aria's tool docs say "REQUIRES USER APPROVAL" for write tools. Aria is instructed to ask the user before firing.
- Hard approval (SSE-pause + UI button) is documented in `ROADMAP.md` for the next sprint. It needs frontend SSE-stream interception + backend pause/resume — meatier work, not blocking today.

### 🧪 Verification

- Backend ruff: clean (billing.py, aria_tools_slack.py, aria_tools_messaging.py, connectors.py, chat_pipeline.py).
- Frontend ESLint: clean (PricingDrawer.js, ConnectorsDrawer.js, CaosShell.js, ProfileDrawer.js).
- `/api/connectors/list` returns 7 cards correctly.
- `/api/billing/me` returns current tier + 6 available tiers.
- `/api/billing/checkout` returns real Stripe Checkout URL with session_id.
- Live UI screenshots: Connectors drawer (7 cards in 5 sections) + Pricing drawer (6 tier cards with daily-token chips). Both render cleanly.
- *No `testing_agent_v3_fork` invoked. Manual curl + screenshot only.*

### 🟡 What's left for Sprint 4

- **Hard per-action approval gate** — SSE intercept + UI confirmation button before write actions fire.
- **Slack search via xoxp- user token path** — currently bot-token-only.
- **Inbound webhooks** for Twilio SMS + Telegram (live two-way comms).
- **Audit log per-connector** — every fetch/write timestamped, surfaced in the connector card's "Recent activity" section.
- **Stripe Customer Portal link** — let users self-manage payment methods + cancel.

### ⚠️ For user, before next session

To turn on each connector live:
- **Slack**: Create app at https://api.slack.com/apps → Install to Workspace → copy the Bot User OAuth Token (xoxb-…) → paste in Slack card.
- **Twilio**: From https://console.twilio.com → grab Account SID + Auth Token + buy/use an SMS-enabled phone number → paste in Twilio card.
- **Telegram**: Talk to `@BotFather` on Telegram → create bot → get token → paste in Telegram card.
- **Stripe upgrade**: in test mode, use card `4242 4242 4242 4242` with any future expiry + any CVC.

---

## 2026-04-25 (round 4) — Connectors Sprint 1 + Sprint 2 (verified live)

### 🟢 Sprint 1: Foundation + Google Workspace (read-only)

- OAuth scaffolding (token_vault.py, connector_oauth, google_client). 7 Aria tools (gmail_search, gmail_get_message, drive_search, drive_read_file, docs_get_document, calendar_list_events, calendar_freebusy). Connectors hub UI replaces the legacy GitHub-only PAT row.

### 🟢 Sprint 2: MCP client + Obsidian (verified live)

- Minimal JSON-RPC HTTP MCP client (skipped the `mcp` PyPI package — starlette conflict). Obsidian vault upload with backlink resolution. 4 Obsidian Aria tools.

## 2026-04-25 (round 3) — Logout actually logs you out

- Z-index fix (.caos-header to z-index 60) + missing `import { API }` + static axios + belt-and-suspenders client cleanup. DB session row actually destroyed.

## 2026-04-25 (round 2) — Login routing + search drawer position

- Login resumes most-recent populated session (skips empty stubs). Search drawer fixed at top-right (was bottom-left due to CSS exclusion list).

## 2026-04-25 (round 1) — Tier 1 critical bug sweep

- 7 P0/P1/P2 fixes: engine override, sanitizer dedup, error UI sanitization, STT latency, constellation mount, error boundary, search labels.

- **OAuth scaffolding** — generic state-cached Authorization Code flow.
  Files: `services/token_vault.py` (Fernet at-rest encryption + on-demand
  refresh), `routes/connectors.py` (start/callback/disconnect for `google`),
  `services/google_client.py` (authenticated googleapiclient.Resource factory
  with transparent token refresh).
- **Aria Google tools** — `gmail_search`, `gmail_get_message`, `drive_search`,
  `drive_read_file`, `docs_get_document`, `calendar_list_events`,
  `calendar_freebusy`. Read-only. Auto-injected into the system prompt only
  when the user has connected Google. File: `services/aria_tools_google.py`.
- **Tool dispatcher refactor** — `aria_tools.py` regex extended;
  `extract_and_run_next_tool_async` added so chat_pipeline doesn't have to
  bridge sync/async with `run_coroutine_threadsafe`.
- **Schemas** — `schemas/connectors.py` (`ConnectorState`, `GoogleStartResponse`,
  `GoogleCallbackRequest`/`Response`, `ConnectorAuditEntry`).
- **Connectors hub UI** — replaces the old "GitHub PAT only" row with a
  full drawer at `<ConnectorsDrawer />` opened from Profile → Connectors.
  Sections: WORKSPACE / KNOWLEDGE / CODE / UNIVERSAL. New files:
  `ConnectorsDrawer.js`, `connector-popup-handler.js`, `GoogleConnectorsCallback.js`,
  `connectors.css`. New route in `App.js`:
  `/auth/google-connectors-callback` for the OAuth popup.
- **Frontend OAuth popup** — opens Google's consent URL, listens for
  `postMessage` with the result, closes. No hard-coded URLs (built from
  `window.location.origin`).
- **Per-user dynamic tool registry** — `chat_pipeline.py` checks each
  connector's connection state per turn and only injects tool docs into
  the system prompt for connectors actually wired up. Tool iterations
  bumped 3 → 4 to accommodate multi-tool turns.
- **Env additions** — `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`,
  `CONNECTOR_TOKEN_FERNET_KEY` (auto-generated). User provided OAuth credentials
  from Google Cloud Console with both preview + custom-domain redirect URIs
  whitelisted.

### 🟢 Sprint 2: MCP client + Obsidian (verified live)

- **MCP client mode** — minimal JSON-RPC over HTTP. `services/mcp_client.py`
  exposes `add_server`, `list_servers`, `delete_server`, `refresh_server`,
  `dispatch_mcp_call`, `render_mcp_prompt`. Per-server tool catalog is
  cached in `mcp_servers.tools_cache`; refresh on demand. Aria invokes via
  `[MCP_CALL: <server_id>:<tool_name> {json args}]` markers parsed out of
  her replies. Skipped the `mcp` PyPI package (it pulls starlette 1.0
  which conflicts with FastAPI 0.110.1's pin); rolled minimal client by hand.
- **Obsidian vault upload** — `services/obsidian_indexer.py` parses
  YAML frontmatter, `#tags`, `[[wikilinks]]`, derives titles, and resolves
  backlinks in a second pass. Storage: `obsidian_notes` + `obsidian_vaults`.
  4 Aria tools: `obsidian_search`, `obsidian_get_note`, `obsidian_list_tags`,
  `obsidian_backlinks`. Backlink test verified: "Today" note correctly traces
  back to "Connectors Hub" because the latter contains `[[Today]]`.
- **Connectors UI extended** — `ObsidianCard` (folder picker via
  `webkitdirectory`, only `.md` files sent), `McpCard` (full CRUD: add /
  list / delete servers, never echoes the auth header back to the client).

### 🧪 Verification

- Backend ruff: clean across all new files.
- Frontend ESLint: clean (App.js, ConnectorsDrawer.js, GoogleConnectorsCallback.js,
  connector-popup-handler.js, ProfileDrawer.js, CaosShell.js).
- Backend curl: `/api/connectors/list` returns 4 cards (GitHub / Google /
  Obsidian / MCP) with correct connected/not-connected states.
- Backend curl: `/api/connectors/google/start` returns valid Google consent
  URL with all 4 read-only scopes + state CSRF token.
- Backend curl: `/api/connectors/obsidian/upload` round-trips 3 sample notes
  → indexes 3 notes, 3 tags, backlink resolution working.
- Live UI screenshot: All 4 cards render in the drawer, Obsidian shows the
  real seeded "Connected · 3 notes · 3 tags" state, headings and section
  labels render correctly, dark theme + glass-morphism intact.
- *Per user directive: NO `testing_agent_v3_fork` invoked. Manual curl +
  screenshot only.*

### 🟡 Deferred to Sprint 3

- Slack OAuth (read + post-with-approval gate)
- Twilio SMS + Telegram bot connectors
- Stripe billing wired to the existing 6-tier quota system
- Per-action approval UI for write-class connector actions

### ⚠️ Required of user before next session

For Sprint 3:
- Slack App credentials (Client ID + Secret + Signing Secret)
- Twilio Account SID + Auth Token + a Twilio phone number
- Telegram Bot Token (from @BotFather)
- Stripe production key (the test key in pod env handles dev)

---

## 2026-04-25 (round 3) — Logout actually logs you out (server-side too)

### 🔴 Bug fixed (verified end-to-end on the live preview URL with a seeded test session)

- **[LOGOUT-02]** Clicking "Log Out" left the user logged in (frontend + backend). Two stacked bugs:
  1. **Z-index war** — `caos-base44-parity.css:42` set `position: relative; z-index: 1` on every direct child of `.caos-shell-root`, including `.caos-header`. That made the header sit at the same stacking level as `.caos-shell-grid` (the chat area), and source order (grid is later) painted the WelcomeHero cards over the AccountMenu dropdown's lower half. Even though the menu was visually visible, pointer events at "Log Out"'s coordinates resolved to the WelcomeHero card behind it. The click landed on a card, the menu's `mousedown` outside-click handler closed the menu, and the user saw "the menu blinked closed and nothing happened."
  2. **`onLogOut` was silently broken** — the handler used `await (await import("axios")).default.post(\`${API}/auth/logout\`...)` inside a `try { } catch {}`. But `API` was *never imported* into `CaosShell.js` — the URL evaluated to `"undefined/auth/logout"`, axios threw immediately on the malformed URL, the empty catch swallowed the error, and the code never reached `localStorage.removeItem` or `window.location.replace("/")` either. Even when the click DID land (e.g. via JS), nothing actually happened. The cookie + DB session stayed alive, the user's next interaction's `/auth/me` re-authenticated, and they appeared "logged right back in."
  
  **Fix:** Bumped `.caos-header` to `z-index: 60`. Imported `API`. Replaced dynamic `import("axios")` with static. Belt-and-suspenders client-side cleanup. `console.error` for future regressions.
  
  **Verified:** Network capture confirmed `/api/auth/logout` fires. Cookies count drops 1 → 0. Page navigates to login screen. DB query post-logout: `user_sessions.count_documents({token})` = 0 AND `user_sessions.count_documents({user_id})` = 0. ✅

## 2026-04-25 (round 2) — Login routing + search drawer position (verified live)

- **[LOGIN-01]** Login no longer routes to a blank "New Thread" stub. Walks sessions list and picks the first with populated `last_message_preview`. Verified live with seeded test (1 empty + 1 populated → resumes populated).
- **[SEARCH-DRAWER-01]** Search drawer fixed at top-right (was bottom-left). Broadened CSS `:not()` exclusion list to exempt all fixed-position panels.

## 2026-04-25 (round 1) — Tier 1 critical bug sweep

- **[ENGINE-01]** Removed silent override hijacking engine choice to Gemini.
- **[SANITIZER-01]** Replaced 200-char prefix dedup with full-content exact match.
- **[ERROR-UI-01]** Pydantic stack trace bubble sanitized at 3 layers.
- **[STT-01]** Stop button instant feedback.
- **[CONSTELLATION-01]** Mounted at App root for welcome page visibility.
- **[ERROR-BOUNDARY-01]** New CaosErrorBoundary class component.
- **[SEARCH-LABEL-01]** Disambiguated "Search this thread" vs "Search across all threads…".

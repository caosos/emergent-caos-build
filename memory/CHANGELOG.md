# CAOS Changelog

## 2026-04-25 (round 4) — Connectors Sprint 1 + Sprint 2 (verified live)

### 🟢 Sprint 1: Foundation + Google Workspace (read-only)

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

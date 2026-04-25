# Connectors — Sprint Plan

**Status:** Approved by user (Apr 25 2026). Sprint 1 begins after credentials provided.
**Goal:** Give Aria the ability to read/write across the user's external workspace — Gmail, Drive, Docs, Calendar, Slack, Notion, Obsidian, Linear/Jira, Stripe billing, Twilio SMS, Telegram. Wire everything through a single Connectors hub UI in Settings.

## Total estimate

| Sprint | Scope | Credits |
|---|---|---|
| 1 | OAuth + Token Vault + Hub UI + Aria registry refactor + Gmail/Drive/Docs/Calendar (read) | ~150 |
| 2 | MCP client mode + Obsidian (file vault upload) | ~100 |
| 3 | Slack OAuth + Twilio SMS + Telegram + Stripe billing wired to tier system | ~150 |
| **Total** | **Full vision** | **~400** |

User's stated cap: <300. Strategy: Sprints 1+2 (~250) ship the highest-value 70%. Sprint 3 deferred until after launch signal.

---

## Sprint 1 — Foundation + Google Suite (read-only)

### Architecture

```
┌─ Frontend (React) ───────────────────────────────────┐
│  ConnectorsDrawer (new — replaces "GitHub PAT" row   │
│   in Settings; shows card grid)                      │
│   ├─ ConnectorCard × N (Gmail, Drive, Docs, ...)     │
│   │   ├─ State: not-connected | connected | error    │
│   │   ├─ "Connect" → opens popup to backend OAuth    │
│   │   └─ "Disconnect" → revokes + deletes tokens     │
│   └─ ConnectorActivityLog (last fetches per          │
│      connector — reuses error_log pattern)           │
└──────────────────────────────────────────────────────┘
              │ (popup-based OAuth)
              ▼
┌─ Backend (FastAPI) ──────────────────────────────────┐
│  /api/connectors/                                    │
│   ├─ GET  /list                  → user's connector  │
│   │                                states            │
│   ├─ POST /<provider>/start      → returns Google    │
│   │                                consent URL       │
│   ├─ GET  /<provider>/callback   → exchanges code,   │
│   │                                stores encrypted  │
│   ├─ POST /<provider>/disconnect → revokes + deletes │
│   │                                tokens            │
│   └─ GET  /<provider>/status     → connection health │
│                                                      │
│  services/connector_oauth.py                         │
│   - generic OAuth2 state-machine                     │
│   - shared between Google, Slack, Notion later       │
│                                                      │
│  services/token_vault.py                             │
│   - Fernet encrypt/decrypt at rest                   │
│   - Refresh-token-on-demand wrapper                  │
│                                                      │
│  services/google_client.py                           │
│   - Returns authenticated google-api-python-client   │
│     instance for a given user + service              │
│                                                      │
│  services/aria_tools_registry.py (refactor)          │
│   - Per-user dynamic tool list based on connectors   │
│   - Aria's system prompt now enumerates available    │
│     tools per turn                                   │
└──────────────────────────────────────────────────────┘
              │
              ▼
┌─ MongoDB ────────────────────────────────────────────┐
│  connector_tokens {                                  │
│    user_email: str,                                  │
│    provider: "google" | "slack" | ...,               │
│    encrypted_access_token: bytes,                    │
│    encrypted_refresh_token: bytes,                   │
│    expires_at: ISO datetime,                         │
│    scopes: [str],                                    │
│    created_at, updated_at                            │
│  }  (unique compound index on user_email+provider)   │
│                                                      │
│  connector_audit_log {                               │
│    user_email, provider, tool, args_summary,        │
│    success: bool, error: str?, latency_ms,          │
│    created_at                                        │
│  }                                                   │
└──────────────────────────────────────────────────────┘
```

### New files

| File | Purpose | LOC est |
|---|---|---|
| `backend/app/routes/connectors.py` | Per-provider start/callback/disconnect routes | 220 |
| `backend/app/services/connector_oauth.py` | Generic OAuth2 state machine (reusable for Slack/Notion later) | 160 |
| `backend/app/services/token_vault.py` | Fernet encrypt/decrypt + refresh-on-demand | 110 |
| `backend/app/services/google_client.py` | Authenticated Google API client factory | 140 |
| `backend/app/services/aria_tools_google.py` | Gmail/Drive/Docs/Calendar tool implementations | 280 |
| `backend/app/schemas/connectors.py` | Pydantic models | 80 |
| `frontend/src/components/caos/ConnectorsDrawer.js` | Drawer with card grid | 220 |
| `frontend/src/components/caos/ConnectorCard.js` | Single connector card with state machine | 140 |
| `frontend/src/components/caos/connector-popup-handler.js` | OAuth popup → postMessage handler | 70 |
| `frontend/src/components/caos/connectors.css` | Card grid styles | 90 |

### Modified files

| File | Change | Impact |
|---|---|---|
| `backend/app/services/aria_tools.py` | Move dispatch logic to registry; auto-load enabled connectors per turn | refactor only, no behaviour change for existing GitHub/web_fetch |
| `backend/app/services/chat_pipeline.py` | Build per-user tool list before LLM call; inject tool descriptions in system prompt | 1 function added |
| `backend/server.py` | Mount `/api/connectors` router | 1 line |
| `frontend/src/components/caos/SettingsDrawer.js` (or wherever GitHub PAT lives) | Replace GitHub-PAT row with "Connectors →" entry that opens `<ConnectorsDrawer />` | 5 lines |
| `frontend/src/components/caos/CaosShell.js` | Mount `<ConnectorsDrawer />` | 3 lines |
| `backend/.env` | Add `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `CONNECTOR_TOKEN_FERNET_KEY` | 3 keys |

### Aria tools added (Sprint 1)

| Tool name | Provider | Scope | Description |
|---|---|---|---|
| `gmail_search` | Google | gmail.readonly | List up to 20 messages matching a Gmail search query (`from:`, `is:unread`, etc.) |
| `gmail_get_message` | Google | gmail.readonly | Fetch full body + headers of a specific message |
| `drive_search` | Google | drive.readonly | Find files by name / mime type / folder |
| `drive_read_file` | Google | drive.readonly | Read text content of a Doc/Sheet/text file (size capped) |
| `docs_get_document` | Google | documents.readonly | Get structured Google Doc content |
| `calendar_list_events` | Google | calendar.readonly | List events in a date range |
| `calendar_freebusy` | Google | calendar.readonly | "When am I free between 9am-5pm next Tuesday?" |

All tools return Pydantic-serialized JSON. The dispatcher trims long content before passing to Aria so we don't blow the context window.

### Per-action approval gates — deferred to Sprint 3

Sprint 1 is read-only. No write actions yet → no approval UI needed. When Sprint 3 adds Slack-post / Calendar-create / Gmail-send, we'll add a generic `ApprovalGate` component that intercepts the `tool_call` event from the SSE stream and prompts the user before executing.

### OAuth flow (Google)

1. User opens Connectors drawer → clicks "Connect Google".
2. Frontend calls `POST /api/connectors/google/start` → backend returns Google consent URL with all 4 scopes pre-attached.
3. Frontend opens that URL in a popup (`window.open` 600×700).
4. User consents on Google → Google redirects popup to `/auth/google-connectors-callback?code=...&state=...`.
5. Backend `GET /api/connectors/google/callback` exchanges code for tokens, encrypts with Fernet, stores in `connector_tokens`, sends `postMessage` back to opener.
6. Popup auto-closes. Drawer refreshes connector states.

`state` parameter carries a short-lived (5 min) one-time JWT bound to the user's session_token to prevent CSRF.

### Refresh strategy

No background worker. Refresh on demand:
- When Aria invokes a Google tool, `token_vault.get_access_token(user, provider)` is called.
- If `expires_at` is in the past or within 60 seconds: use refresh_token to get a new access_token, update DB, return.
- If refresh_token itself rejected (revoked by user on Google's side): mark connector as `needs_reauth`, surface in card.

Simpler than a worker, no race conditions, only refreshes when actually needed.

### Test plan (Sprint 1)

1. Manual flow: connect Google in test account → verify tokens stored encrypted (check DB row, confirm bytes ≠ plain string).
2. Aria tool call: `"What did I get from GitHub today?"` → should call `gmail_search` with `from:noreply@github.com newer_than:1d` → return summarized list.
3. Refresh: manually expire `expires_at` in DB → next tool call should refresh and update DB.
4. Disconnect: click Disconnect → verify token row deleted AND Google's revocation endpoint called.
5. Token-vault crypto: encrypt/decrypt round-trip Python unit test.
6. UI: Card states render (not-connected → connected → needs-reauth → error).

No `testing_agent_v3_fork` (per user's strict no-swarm rule). All manual + curl + screenshot.

---

## Sprint 2 — MCP Client Mode + Obsidian (~100 credits)

### MCP client (~80 credits)

- Implement Model Context Protocol client per Anthropic's spec (websocket / stdio transport).
- New file: `backend/app/services/mcp_client.py`.
- Connectors hub gets a new card: **"Add MCP Server"** with URL input.
- Each connected MCP server's `tools/list` is enumerated and merged into the user's Aria tool registry on each chat turn.
- Aria's system prompt: "You also have access to user-connected MCP tools: {list}".
- Per-MCP-server enable/disable toggle in the card.
- Storage: `mcp_connections` collection (server URL, name, enabled, optional auth headers).

This single feature unlocks Notion, Linear, Stripe (as MCP), Sentry, Filesystem, Postgres, anything with an MCP server. Massive ROI.

### Obsidian (~20 credits)

- File-based, no OAuth. User uploads vault as a `.zip` or selects local folder via FileSystem API.
- Backend `obsidian_indexer.py` walks the vault, parses Markdown, extracts wikilinks + tags + frontmatter.
- Stored in `obsidian_notes` collection per user.
- Aria tools: `obsidian_search`, `obsidian_get_note`, `obsidian_list_tags`, `obsidian_backlinks`.
- Re-upload re-indexes (no live sync — keep it dumb-simple).

---

## Sprint 3 — Bespoke Connectors + Stripe Billing (~150 credits)

### Slack (~70 credits)

- OAuth via the generic `connector_oauth.py` from Sprint 1 (just different scopes + auth URL).
- Scopes: `channels:read`, `channels:history`, `chat:write` (write requires per-action approval).
- Aria tools: `slack_list_channels`, `slack_search_messages`, `slack_post_message` (gated).

### Twilio SMS + Telegram (~50 credits combined)

- Twilio: API key based (Account SID + Auth Token + From-number). Aria tools: `sms_send` (gated), `sms_inbox_list`. Inbound SMS to a Twilio phone number → webhook → stored as message → Aria can be polled.
- Telegram: Bot token. Aria tools: `telegram_send_message`, inbound messages via webhook.
- Both use a shared `messaging_inbox` collection for two-way comms.

### Stripe billing → tier system (~30 credits)

- Stripe test key already in pod env (per system prompt).
- Wire `stripe.checkout.sessions.create` for tier upgrade flow.
- Webhook endpoint receives `checkout.session.completed` → bumps user's tier in `user_profiles`.
- Tier system already exists in `token_quota.py` — just add the upgrade path + webhook handler.
- No new tier UI needed (already in admin dashboard).

### Per-action approval UI (~30 credits, applies to all Sprint 3 write actions)

- New component `<ApprovalGate />` intercepts tool calls flagged `requires_approval: true`.
- Renders inline in chat: "Aria wants to send to #team-eng with content 'X'. [Approve] [Cancel] [Always allow for this connector]"
- "Always allow" sets a per-tool toggle in `user_profiles.approved_tools`.

---

## Credentials checklist

### Sprint 1 (need from user before I can start)

1. **Google Cloud Console OAuth client** — needs:
   - Go to https://console.cloud.google.com/apis/credentials
   - Create or select a project (call it "CAOS Connectors")
   - Enable APIs: Gmail API, Google Drive API, Google Docs API, Google Calendar API
   - Create OAuth 2.0 Client ID, type "Web application"
   - **Authorized JavaScript origins**: paste these EXACTLY
     ```
     https://caos-workspace-1.preview.emergentagent.com
     https://caosos.com
     ```
   - **Authorized redirect URIs**: paste these EXACTLY
     ```
     https://caos-workspace-1.preview.emergentagent.com/auth/google-connectors-callback
     https://caosos.com/auth/google-connectors-callback
     ```
   - Copy the **Client ID** and **Client Secret** — give to me to put in `backend/.env`.

2. **Fernet key** for token encryption — I'll generate this server-side, no user action needed. Stored as `CONNECTOR_TOKEN_FERNET_KEY` in `backend/.env`.

### Sprint 2 (no credentials)

MCP servers chosen by user via UI. Obsidian is just a vault upload.

### Sprint 3 (need from user before that sprint starts)

1. **Slack** — Slack App created at https://api.slack.com/apps with the right scopes; Client ID + Secret + Signing Secret.
2. **Twilio** — Account SID + Auth Token + a Twilio phone number with SMS enabled.
3. **Telegram** — Bot Token from @BotFather.
4. **Stripe** — using existing pod test key. For production, needs live key (later).

---

## Hard rules during execution

- No `testing_agent_v3_fork`. Manual curl + screenshot only.
- Surgical search_replace. No rewrites.
- No emoji in source files unless user requests.
- Comment EVERY file with the "DO NOT HARDCODE THE URL" reminder where OAuth touches it.
- Update `/app/memory/test_credentials.md` with any test Google account used.
- Update `/app/memory/CHANGELOG.md` after each sprint.
- Update `/app/memory/TROUBLESHOOTING_BULLETIN.md` if new bugs found.

## Sprint 1 sequencing (single session)

1. Backend foundation (token_vault, connector_oauth, schemas, routes/connectors.py) — ~50 credits
2. Google API client + 4 Aria tools (Gmail/Drive/Docs/Calendar read) — ~40 credits
3. Aria tools registry refactor + system prompt injection — ~15 credits
4. Frontend ConnectorsDrawer + ConnectorCard + popup-handler — ~35 credits
5. Wire into Settings, smoke test, manual verification — ~10 credits

Total: ~150 credits, one focused session, no questions mid-flight.

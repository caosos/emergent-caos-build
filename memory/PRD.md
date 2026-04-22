# CAOS — Emergent Replatform PRD (LIVE)

## Original Problem Statement
Port Base44 CAOS (Deno serverless) to clean React + FastAPI + MongoDB on Emergent. Preserve behaviors, governance, and UX from the Base44 live build. Aria = persona, CAOS = platform.

## Authoritative Contracts (binding)
- System Blueprint v2 — sections 0–20
- TSB Log Part 1+2 — TSB-001 through TSB-061
- File sizes: 200 preferred / 400 soft max / 800 acceptable if clean and working (owner directive Apr 20, 2026)
- GOV v1.2 Amendment A: ≥300-line files get extractions, not inline growth
- Aria ≠ CAOS: authority domain separation (§0.8)
- Pull-only awareness (§0.9)
- Build → Test → Lock
- Edit tracking: `Changed: <file> +N lines` after every modifying response
- TTS paths locked: OpenAI tts-1 (bubble) / browser speechSynthesis (input bar fallback)
- Active chat model: Claude (default) → OpenAI → Gemini → Grok (BYO key deferred)

## Providers
| Provider | Key source | Status |
|---|---|---|
| Anthropic Claude (default) | Emergent Universal Key | ✅ Live |
| OpenAI gpt-5.2 | Emergent Universal Key | ✅ Live |
| Google Gemini | Emergent Universal Key | ✅ Live |
| xAI Grok | User XAI_API_KEY (BYO) | Deferred |

## Implemented on Emergent (cumulative, through Apr 20, 2026)

### Backend
- `/api/caos/sessions`, `/messages`, `/artifacts`, `/continuity`
- `POST /api/caos/chat` — non-streaming full pipeline
- `POST /api/caos/chat/stream` — SSE with `meta` → word-by-word `delta` → `final` events (TSB-036 parity: Option A)
- Memory CRUD: `/memory/save`, `/memory/{id}` — structured + personal_facts + global bin
- `/voice/transcribe` — forced whisper-1 (Emergent proxy limitation)
- `/voice/tts` — tts-1 primary, fail-soft on proxy 500 (currently 500s at proxy layer; frontend falls back to browser speechSynthesis)
- `/runtime/catalog`, `/runtime/settings`
- `/files` upload/link, `/profile/{email}` upsert/get (now incl. date_of_birth, full_name, role)
- `tiktoken` token metering, retention explanations, rehydration ordering

### Frontend — Base44 parity achieved
- **ShellHeader** — 3-col: identity chip + hamburger + inspector menu (L) / CAOS + subtitle (C) / thread pill + search + live WCW meter (R)
- **InspectorMenu** (NEW) — hamburger dropdown with Desktop/New Thread/Previous Threads/Profile/Engine (inline sub-menu)/Log Out
- **EngineChip** above composer — single pill, 4-provider dropdown
- **SelectionReactionPopover** — 31 emojis w/ frequency tracking, reply input, browser speechSynthesis Read, sonner toasts
- **SearchDrawer** — full-text search with `<mark>` yellow highlighting + match count
- **ThreadMiniMeter** — per-thread WCW bar on every rail + previous-threads card (provider-aware 200K/1M)
- **LatencyIndicator** — per-message badge (3 tiers)
- **ProfileDrawer** (rewrite) — avatar + role chip, Files/Photos/Links tabs, Email/Member/Role/Birthday(edit), Permanent Memories link, Remember/Game/Dev/Multi-Agent/Console toggles, Voice & Speech link, Delete Account
- **VoiceSettings modal** — 6 OpenAI voices (alloy/echo/fable/onyx/nova/shimmer), Test preview, speed slider 0.5–2.0×
- **ProfileMemoryView** — add/edit/delete permanent memories inline
- **ProfileFilesView** — tabbed Files/Photos/Links with search
- **Composer** — auto-grow 1–6 rows, Shift+Enter newline, pulsing red mic, toast on permission/device errors, live-stream transcript ribbon, cumulative WebM chunks (fixes header issue)
- **MessagePane** — optimistic user message + typing dots + streaming cursor (▌) for SSE deltas
- **CaosShell** — sonner Toaster mounted globally, starfield background

### UX micro-wins
- Optimistic user message (appears instant on send)
- 3-dot typing indicator for pending assistant (pre-stream)
- Streaming cursor for in-progress SSE delta rendering
- Click-outside + Escape on all popovers/drawers/modals
- Rail-brand + rail-footer hidden (identity lives in header only)
- Live-transcript ribbon (breathing purple/blue) while mic records
- Mic pulsing red ring while recording

## Menu Cleanup — Kill the Redundancy (Apr 21, 2026)
User flagged three competing menu systems. Fixed:
- **Killed the identity-chip dropdown** in `ShellHeader`. The MICHAEL chip is now click-to-open-profile (one action). Removed `showIdentity` state, `ChevronDown`, useRef, outside-click listener, and the dropdown JSX (about 45 lines).
- **Left rail now closed by default** (`useState(false)` instead of `true`). Base44 parity — the sidebar opens only when you click the rail-toggle button. Earlier it was eating 25% of the screen on load and hiding the hamburger menu when opened.
- **Piped `onOpenSwarm` through** `ShellHeader` → `InspectorMenu` so the **Agent Swarm · E2B** item is in the hamburger menu alongside New Thread / Previous Threads / Profile / Engine / Log Out. Verified clickable via automation.

## Call-Prep Build (Apr 20, 2026 — afternoon)
Four polish items ahead of tomorrow's Emergent partnership call.

### Thought Stash ("+ Thought" button)
- Composer now has a `+` button (between attach/read and mic). Click it (or Ctrl+Shift+Enter) to stash the current textarea content as a pending thought, clearing the box for the next one.
- Stashed thoughts pile up in a purple card above the composer, numbered, with individual `×` removal + "Clear all". Persisted to localStorage so they survive page reloads.
- Send concatenates all stashed thoughts + current draft into ONE compound message (joined with blank lines), clears both. User's stated need: "follow up and add to things you're thinking about instead of having to write it down and then later putting it in…"

### Profile Chip + Sign Out
- Top-right identity chip now shows `authenticatedUser.picture` (Google avatar) when available, falls back to initial letter.
- Display name prefers `authenticatedUser.name` over localStorage guesses.
- Identity dropdown adds an email subtitle + **Sign out** menu item. Sign-out POSTs `/api/auth/logout` (clears DB session + cookie) then redirects to `/`.

### `/api/health` Dashboard Endpoint
- Public (no auth) aggregated status check. Probes: Mongo collections, Emergent LLM proxy `/v1/models`, OpenAI voice key `/v1/models`, E2B + GitHub config, object storage, auth.
- Response verified: `{"ok": true, "subsystems": {...}}` — all six green except GitHub (expected, no token yet).
- Useful for (a) demo talking points, (b) a future status chip in the UI.

## Security + Scale Hardening (Apr 20, 2026 — dawn)
Tackled all 5 items from the Emergent team's code review.

### 1. MongoDB Indexes (`app/startup.py`, wired into `on_startup`)
- 14 compound indexes created on every hot collection: sessions(user_email, session_id), sessions(user_email, updated_at DESC), messages(session_id, timestamp), user_profiles(user_email UNIQUE), user_files(user_email, created_at DESC), user_files(user_email, session_id), receipts(session_id, created_at DESC), thread_summaries(session_id), context_seeds(session_id), global_info_entries(user_email, lane), user_sessions(session_token UNIQUE), user_sessions(user_id, expires_at), users(email UNIQUE), users(user_id UNIQUE).
- Idempotent — safe on every boot.

### 2. Emergent-managed Google OAuth (replaces client-supplied user_email)
- New `auth_service.py` + `routes/auth.py` implementing the exact playbook flow:
  - `POST /api/auth/process-session` — exchanges the one-time `session_id` from the URL fragment with Emergent's `oauth/session-data` endpoint, upserts `users`, records a 7-day `user_sessions` row, sets an httpOnly `samesite=none; secure` cookie.
  - `GET /api/auth/me` — returns the current user or 401.
  - `POST /api/auth/logout` — deletes the session + clears cookie.
- `require_user` FastAPI dependency reads either the `session_token` cookie OR a `Bearer` header, validates against `user_sessions`, rejects expired sessions, returns the user dict.
- **Every `/api/caos/*` route is now gated** via `dependencies=[Depends(require_user)]` on the router. Unauthenticated calls return 401.
- `/files/upload` + `/files/link` + `/files/{id}/download` now use the authenticated user's identity instead of a client-supplied email, with owner-check on downloads (IDOR hardening).
- **Frontend**: `AuthGate` probes `/auth/me` on boot, renders `LoginScreen` on 401 or `CaosShell` on 200. `LoginScreen` has a polished "Continue with Google" CTA. `AuthCallback` at `/auth/callback` processes the OAuth return and redirects to `/`. `axios.defaults.withCredentials = true` so cookies flow.
- **Axios 401 interceptor** — if any `/api/caos/*` call 401s mid-use (expired session), auto-reloads `/` to show the login screen.

### 3. Object Storage (replaces ephemeral `/app/backend/uploads/`)
- New `services/object_storage.py` wraps Emergent's object-storage REST API. `init_storage()` runs at FastAPI startup, calls `POST /storage/init` with the Universal Key, caches the returned storage_key.
- `file_storage.py` rewritten: `save_upload(file, user, session_id)` uploads bytes via `PUT /storage/objects/<path>` and returns the metadata dict. Gracefully falls back to local disk only if storage init failed.
- Download route serves object-storage files via `GET /storage/objects/<path>` when `storage_backend == "emergent_objstore"`, falls through to local file response otherwise.
- Files outlive pod restarts. Path scheme: `caos/uploads/<user_id>/<uuid>.<ext>`.

### 4. CORS fix for cookie flow
- Replaced `allow_origins=[*]` + `allow_credentials=true` (browser-illegal combo) with `allow_origin_regex=".*"` when env has `CORS_ORIGINS=*`, which echoes the caller origin and keeps credentials working. Explicit list honored when a real origin is configured.

### 5. Frontend resilience
- Low-level helpers (`load*`) already run inside try/catch wrappers at the caller level; remaining polish is the 401 interceptor above (single-point-of-truth for auth-expiry UX).

## Voice I/O Unblocked — Direct OpenAI Path (Apr 20, 2026 — late)
- **Root cause confirmed:** Emergent audio proxy's upstream OpenAI key is invalid (HTTP 401 on whisper-1, 500 on tts-*).
- **Fix:** User provided a direct `OPENAI_API_KEY` (`sk-proj-...`). Stored in `/app/backend/.env`.
- **`voice_service.py` rewritten** with preference order:
  1. Direct OpenAI SDK (`openai.AsyncOpenAI`) when `OPENAI_API_KEY` is present — unlocks `gpt-4o-mini-tts` and `gpt-4o-mini-transcribe` (the 2026 defaults, blocked on the Emergent proxy allow-list).
  2. Graceful fallback chain: `gpt-4o-mini-tts` → `tts-1` → `tts-1-hd` (and `gpt-4o-mini-transcribe` → `whisper-1` for STT).
  3. Legacy Emergent proxy path retained as last-resort if no direct key.
- **Verified end-to-end:**
  - `POST /api/caos/voice/tts` with `model=gpt-4o-mini-tts` → 53KB of real audio_base64 (audio/mpeg), voice=nova.
  - `POST /api/caos/voice/transcribe` with `model=gpt-4o-mini-transcribe` → correct transcription `"Hello world, this is a test."`
- Read Aloud + Mic input should now Just Work™ in the UI — no proxy dependency. Support ticket to Emergent still recommended so they rotate the proxy's upstream key.

## Voice I/O Root-Cause Identified + Support Ticket Armed (Apr 20, 2026)
- **Ran a diagnostic curl battery against `https://integrations.emergentagent.com/llm`** and caught the exact failure: `POST /audio/transcriptions` with `model=whisper-1` returns **HTTP 401** with `"Incorrect API key provided: sk-proj-********_AIA"`. The upstream OpenAI project key Emergent's proxy uses for audio routes has been invalidated.
- `tts-1` and `tts-1-hd` return HTTP 500 with empty body — almost certainly the same root cause masked as generic server error.
- `/v1/models` shows the audio allow-list is exactly `{tts-1, tts-1-hd, whisper-1}` — newer models (`gpt-4o-mini-tts`, `gpt-4o-mini-transcribe`) return HTTP 400 "Invalid model name". User's hypothesis was right in direction (try newer models) but the proxy rejects them entirely.
- **Fixed** `voice_service.py` to stop masking the 401 as an empty transcript; now returns `{"text": "", "error": "...", "platform_note": "..."}` so the UI can show actionable info.
- **Delivered an armed support letter** with the concrete 401 evidence + `sk-proj-...AIA` key snippet, asking Emergent to rotate the upstream key and expand the audio allow-list to include `gpt-4o-mini-tts` / `gpt-4o-mini-transcribe`.

## GitHub Adapter — Swarm Reaches Beyond /app (Apr 20, 2026 — overnight pt 3)
- **New module** `backend/app/services/github_tools.py`: 8 read-only GitHub REST API tools the Supervisor can call as `type="tool"` steps:
  - `gh_whoami()` — auth sanity check
  - `gh_list_repos(visibility, limit)` — user's repos
  - `gh_read_file(repo, path, ref)` — file contents from any branch/tag
  - `gh_list_prs(repo, state, limit)` / `gh_read_pr(repo, number)` — PRs + changed files
  - `gh_list_issues(repo, state, limit)` — open issues (PRs filtered out)
  - `gh_search_code(repo, query, limit)` — GitHub code search
  - `gh_file_history(repo, path, limit)` — commit history for a file
- All tools require `GITHUB_TOKEN` in backend env; without it, each call returns a crisp "(GITHUB_TOKEN not configured — please set it in /app/backend/.env)" so the Critic writes useful guidance instead of crashing.
- httpx-based, 15s timeout, 8KB output cap, read-only by design. PAT needs `repo` (private) or `public_repo` scope; optional `read:user` / `read:org`.
- Merged into `TOOL_REGISTRY` and `TOOL_DOCS` so the Supervisor is automatically aware of both local (`caos_*`) and GitHub (`gh_*`) tools.

## Swarm Tools — Real Repo Awareness (Apr 20, 2026 — overnight pt 2)
- **New module** `backend/app/services/swarm_tools.py`: server-side read-only tools that the Swarm Supervisor can call:
  - `caos_grep(pattern, path, file_glob)` — recursive grep across `/app` (excludes node_modules/.git/__pycache__/dist/build/.next/.venv, 15s timeout, 6KB output cap)
  - `caos_read_file(path, start_line, end_line)` — line-ranged file read with line numbers
  - `caos_ls(path, max_depth)` — directory listing (hides noise dirs)
  - `caos_git_log(limit)` — recent commits
  - All tools path-safe (reject escapes outside `/app`), clipped output, no writes, no network.
- **Swarm now supports two step types**: `type="tool"` (runs server-side in our process) and `type="python"` (runs in E2B sandbox). Supervisor prompt teaches Claude Sonnet 4.5 when to use each.
- **UI**: step cards now show a green "tool · caos_grep" chip or blue "python" chip so you can see which path ran.
- **Verified end-to-end**: asked the Swarm "Find voice service files and tell me why TTS might be failing." It planned 3 tool steps (grep → ls → read_file), found `/app/backend/app/services/voice_service.py`, read it, and wrote a correct diagnosis pointing at the Emergent proxy 500s. That's the "Aria reads its own code" vision working.

## Phase 4 — Agent Swarm v1 (Apr 20, 2026 — overnight)
- **Backend** `/app/backend/app/services/swarm_service.py` (~140 lines): Supervisor (Claude Sonnet 4.5 → JSON plan) → Worker (E2B `Sandbox.create()` runs each step's Python, preserves state across steps, 45s timeout per step) → Critic (Claude Sonnet 4.5 reads stdout + writes final answer).
- **Routes**: `POST /api/caos/swarm/run` (non-streaming) and `POST /api/caos/swarm/stream` (SSE: `phase` → `plan` → `step` × N → `final`).
- **Frontend** `SwarmPanel.js` (~180 lines): modal with task input, Run button, live phase chips (Plan / Execute / Review / Done), rendered plan, per-step sandbox stdout/stderr, final answer card.
- **Inspector menu** gained an "Agent Swarm · E2B" entry to open the panel.
- Verified end-to-end: "Compute 7 factorial" → plan step → E2B prints `7! = 5040` → Critic writes "7! = 5040".

## Auto-route to Gemini on image attach (Apr 20, 2026 — overnight)
- `useCaosShell.sendMessage` now checks session attachments; if an image is present and the active provider isn't Gemini, it transparently overrides `provider=gemini` / `model=gemini-3-flash-preview` for that turn and surfaces a status toast. Keeps the user's default engine choice intact for non-image turns.

## UI Polish — Base44 Parity (Apr 20, 2026 — midnight)
- **Auto-clearing status banner** — `MessagePane` and `Composer` both auto-dismiss transient status strings after 4s. No more "Read aloud is unavailable" or similar banners sticking around. Fade-out animation on the status chip.
- **Message bubble visual match** — big solid violet-gradient user bubbles (right-aligned, asymmetric bottom-right corner, violet glow shadow); subtle dark AI bubbles with a purple avatar orb on the left; action chips restyled as pill buttons below each bubble.
- **Composer rebuilt** — circular icon buttons for attach/speaker/mic, gradient purple circular send button, roomier padding, blurred glassmorphic shell.

## File Attachments → AI Context (Apr 20, 2026 — late)
- Multi-file upload (up to 10) via Composer `<input multiple>`; toast confirms "Attached N files — the AI can now see them".
- Backend `chat_pipeline` now fetches `user_files` for the active `session_id` and injects them into the system prompt under a new "Attachments in this thread" block.
- For Gemini provider: full binary file content is attached to `UserMessage.file_contents` via `FileContentWithMimeType` (verified end-to-end — Gemini 3 Flash correctly described a red 256×256 PNG).
- For Claude/GPT: filenames + mime types + sizes appear in system prompt (emergentintegrations currently restricts binary attachments to Gemini); users are nudged to switch engine for vision tasks.

## Read Aloud Reliability Fix (Apr 20, 2026 — late)
- `useVoiceIO.speakText` now waits briefly for `voiceschanged` event (async voice loading on Linux/Chrome) before giving up.
- If no voices are available, throws a specific actionable error ("No TTS voices on this system. On Ubuntu: sudo apt install speech-dispatcher") instead of cryptic "unavailable in this browser".
- `MessagePane.handleReadAloud` surfaces the actual error message to the user.

## Multi-Agent Synthesizer (Apr 20, 2026)
- `/api/caos/chat/multi` now returns a 4th `synthesis` field alongside the 3-column fan-out.
- Synthesizer = Claude Sonnet 4.5, reads Claude + OpenAI + Gemini replies and produces ONE cohesive answer with `[Claude]`, `[GPT]`, `[Gemini]`, or `[All]` citations.
- `MultiAgentMessageGroup` renders synthesized reply by default; raw 3 columns tucked behind a "Show sources" toggle.
- Skipped (silently) when fewer than 2 agents succeed.

## File Sizes (GOV v1.2 compliance restored)
- `useCaosShell.js` 391 ✅ (was 561)
- `useVoiceIO.js` 62 (extracted)
- `useMemoryCrud.js` 68 (extracted)
- `useFilesCrud.js` 55 (extracted)
- `MultiAgentMessageGroup.js` 152
- `multi_agent.py` (backend) 139
- `ProfileDrawer.js` 258
- `SelectionReactionPopover.js` 197
- `MessagePane.js` 199
- `caos-base44-parity.css` 540 (CSS doesn't count)

## Support Ticket Drafted
- Draft letter for Emergent Support re: `/llm/audio/speech` returning HTTP 500 (tts-1 / tts-1-hd) delivered in-chat. User to submit when ready.

## Base44 Parity v2 — Pre-login Welcome + Tour + Equalizer + Admin Auto-Role (Apr 21, 2026)

User showed 20+ screenshots of their live Base44 + Emergent-hosted CAOS and asked for strict parity.
Blueprint locked at `/app/memory/UX_BLUEPRINT.md`. Pain-points documented at `/app/memory/PLATFORM_PAIN_POINTS.md`.

### Shipped (tests 100% green, iteration_16)
- **Pre-login Welcome screen** (`LoginScreen.js`): starfield, 96px pulsing orb, CAOS H1, subtitle, tagline, 2×2 feature grid (Persistent Memory / Web Search / File Intelligence / Voice Ready), Take the Tour primary button, Sign In secondary, Continue as Guest ghost link, footer attribution.
- **5-step Welcome Tour** (`WelcomeTour.js`): modal with 5-dot stepper, Start here → Your threads → Aria remembers → Attach anything → Get started. Persists completion to `localStorage.caos_tour_completed`. Auto-opens first login; re-triggerable from pre-login. Click-outside + Skip tour + Escape all dismiss.
- **Admin auto-assignment** (`auth_service.py`): `ADMIN_EMAILS = {"mytaxicloud@gmail.com"}`. Every login refreshes `role` + `is_admin` in users collection.
- **Auth response includes admin metadata** (`routes/auth.py`): `/api/auth/me` and `/api/auth/process-session` now return `role` + `is_admin`. Verified by 4/4 pytest cases.
- **ProfileDrawer admin fallback**: accepts `authenticatedUser` prop, `isAdmin` check falls back to `authenticatedUser.role/is_admin` when the caos profile record lacks it. Unlocks Developer Mode + Multi-Agent Mode + System Console toggles for admin only.
- **Continue-as-Guest flow** (`AuthGate.js` + `App.js`): sets `localStorage.caos_guest_mode=true`; axios 401 interceptor skips redirect in guest mode; `/auth/me` success + logout both clear the flag.
- **Per-message footer** (`MessagePane.js`): Base44-parity footer row with full date + time + assistant latency (e.g. `Apr 21, 2026 · 1:00 AM · 28.5s`). Green tabular latency chip.
- **Mic equalizer** (`Composer.js` + CSS): 8 bouncing red bars + pulsing dot + RECORDING label while mic is hot. Replaces "is my mic actually on?" uncertainty.

### File sizes (GOV v1.2 compliance)
- `LoginScreen.js` 89 · `WelcomeTour.js` 112 · `AuthGate.js` 94 · `MessagePane.js` 229 · `Composer.js` 295 · `ProfileDrawer.js` 248 · `caos-base44-parity-v2.css` 185 · `auth_service.py` 136 · `routes/auth.py` 81. All under the 400-line soft cap.

## Login Fix — Cross-Origin CORS on Deployed Domains (Apr 21, 2026 — evening)

User reported "Sign-in failed / Network Error" on `swarm-command-4.preview.static.emergentagent.com/auth/callback` after Google OAuth redirect. Root cause investigation revealed two distinct platform behaviors:

1. **Cloudflare edge on `*.preview.emergentagent.com` rewrites `Access-Control-Allow-Origin` to `*`** — regardless of what the FastAPI CORS middleware emits (which correctly echoes the caller origin locally). Browsers REJECT `allow-origin: *` + `allow-credentials: true` + cookies. → "Network Error" before the request ever reaches the backend.
2. **`*.preview.static.emergentagent.com` is a CloudFront CDN** that only accepts cacheable requests (GET/HEAD). POSTs are blocked at the edge with a 403 "distribution is not configured to allow the HTTP request method" page.

**Verified**: On the user's real custom domain `caosos.com`, the same-origin `/api` routing works perfectly:
```
access-control-allow-origin: https://caosos.com
access-control-allow-credentials: true
set-cookie: __cf_bm=...; Domain=caosos.com
```

**Fix shipped**: New `/app/frontend/src/config/apiBase.js` helper exports a runtime-resolved `API` constant:
- If `window.location.hostname === REACT_APP_BACKEND_URL hostname` → use env var (normal preview dev flow).
- If different → fall back to `window.location.origin` (same-origin, safe because Emergent's ingress routes `/api/*` on every app host to the backend service).

All 11 files that previously did `const API = \`${process.env.REACT_APP_BACKEND_URL}/api\`` now `import { API } from "@/config/apiBase"`. This is NOT hardcoding — the env var remains the source of truth when hostnames match. It adapts to wherever the app is served from, which is the only portable way to handle cross-origin credentialed cookies across Emergent's preview/static/custom-domain topology.

**Effect**: Login works correctly on `caosos.com` the moment the user hits "Re-deploy changes". The `.static.` URL remains unusable for auth due to CloudFront POST blocking (platform-side problem, not app-side).

## Next Action Items
- Phase 4: Orchestrated Swarm v1 — LangGraph Supervisor → Claude Opus JSON planner → E2B Sandbox workers → Critic (E2B key already in `.env`).
- Drive app manually — confirm Synthesizer UI + Show-sources toggle feel right end-to-end.
- Port bubble/* extractions (CopyBlock/LinkPreview/YouTubeEmbed) per TSB-025/027/028.
- Gemini provider adapter with native Google Search grounding (unlocks Google Workspace route).
- responseReviewer post-inference gate (TSB-053).
- mbcrEngine + TRH v1 thread rehydration (TSB-054, TSB-029).
- Resend email integration for selection menu email button.
- Google Workspace (Gmail/Drive/Calendar) via Emergent Google auth.

## Base44 Parity v3 — Single Account Chip + Threads-In-Rail + Admin Docs Viewer (Apr 21, 2026 — late)

User voiced (literally — via a recorded note at 00:17) two critical asks before bed:
1. Collapse the redundant menus on the top-left into a single "M MICHAEL ▼" dropdown chip that IS the menu trigger, matching Base44 exactly, and make Previous Threads render INSIDE the left rail with inline rename/flag/delete actions per UX_BLUEPRINT §C/D/E (the previous fork had mapped this out but never coded it).
2. Admin-only in-app documentation viewer so the admin can read `/app/memory/*.md` blueprints/PRD/TSB logs live from inside CAOS (user couldn't see these in the Emergent code editor).

### Shipped
- **Backend**: `PATCH /api/caos/sessions/{id}` and `DELETE /api/caos/sessions/{id}` (owner-only; cascades delete to messages/receipts/summaries/seeds). `is_flagged: bool` added to `SessionRecord`. New `app/routes/admin_docs.py` with `GET /api/admin/docs` (list `.md` files in `/app/memory`) and `GET /api/admin/docs/{filename}` (read). Admin gating by `is_admin=True` or `role=="admin"` on the user session.
- **Frontend — AccountMenu (new)**: the identity chip (`caos-account-menu-chip`) IS the dropdown trigger. One button, no hamburger. Items: New Thread · Previous Threads · Profile · Engine → sub-menu · Agent Swarm · **Admin Docs** (admin-only, yellow badge) · Log Out.
- **ShellHeader**: rewritten to render only `rail-toggle` + `AccountMenu`. `InspectorMenu.js` kept as dead code for rollback safety but no longer imported.
- **PreviousThreadsPanel**: rewritten to render inline inside `.caos-rail-column` when `isEmbedded`. Each card exposes hover-revealed inline actions: 🔵 pencil (rename → inline `<input>` committed on Enter/blur → `PATCH`), 🟡 flag (toggle `is_flagged` → `PATCH`), 🔴 trash (confirm → `DELETE`). Active thread has purple glow border; flagged threads have yellow border + flag icon. Mini-WCW meter per card.
- **CaosShell**: wraps `ThreadRail` in `.caos-rail-column` with relative positioning; when `isRailOpen && showThreadExplorer`, overlays `.rail-threads-embedded-overlay` INSIDE the rail column (`position: absolute; inset: 0; z-index: 25`), preserving the main chat pane visibility. Auto-opens rail when user clicks Previous Threads. Error banner now auto-dismisses after 5s and has a visible dismiss button.
- **AdminDocsDrawer (new)**: full-page backdrop + 1060×780 modal with a left-hand nav of all `.md` files in `/app/memory` and a right-hand pane rendering a lightweight markdown → HTML (headings/lists/code/bold/inline-code). Fetches `/api/admin/docs` on open, lazy-loads doc body on select. Click-outside + X + Escape all close.
- **useCaosShell**: added `renameSession`, `deleteSession`, `toggleFlagSession` with optimistic UI + status toasts + proper current-session fallback when deleted.
- **Z-index fix**: `.caos-shell-root > .caos-header { z-index: 50 }` + `.account-menu-shell { z-index: 50 }` + dropdown `z-index: 100` — prior stacking collision caused the main grid to intercept hit-tests for the dropdown items (drawer/threads wouldn't mount on click).

### File sizes (GOV v1.2 compliance)
- `AccountMenu.js` 150 · `AdminDocsDrawer.js` 146 · `PreviousThreadsPanel.js` 200 · `ShellHeader.js` 93 · `admin_docs.py` 58 · `caos-base44-parity-v3.css` 270. All under 400-line soft cap.

### Verified end-to-end (Playwright with seeded admin cookie)
- Single AccountMenu chip opens → all 7 items visible (including `Admin Docs · ADMIN` yellow badge).
- Click `Admin Docs` → `AdminDocsDrawer` mounts, lists 7 .md files, renders UX_BLUEPRINT / PRD / TSB_LOG content live.
- Click `Previous Threads` → rail auto-opens, `PreviousThreadsPanel` mounts embedded inside rail column with "Search all messages…" input and thread cards.
- Hover a thread card → pencil/flag/trash inline actions appear. Click flag → yellow border + `PATCH` fires + flag icon appears. Click pencil → inline input → Enter → `PATCH` fires + title updates + status toast. Click trash → confirm/cancel → `DELETE` fires + session removed.
- Backend pytest: 16/16 green for new PATCH/DELETE/admin-docs routes.

## Future / Backlog
- RSoD + errorClassifier (TSB-024)
- WCWStatusBadge (color tiers)
- Grok provider adapter (user XAI_API_KEY)
- Onboarding tour (§20)
- CTC ARC Inspector panel
- Emergent platform: TTS `/llm/audio/speech` 500 ticket (draft delivered; browser speechSynthesis fallback unblocks users)

## STT Triplication Fix + Header Parity v4 (Apr 22, 2026 — dawn)

User reported **messages tripling themselves while dictating** and screenshots showed user bubbles with the same sentence repeated 3× inside one message. Also complained header was missing the "Cognitive Adaptive Operating System" subtitle, that the centered search popover obscured the message area, and that the latency chip was missing from assistant replies.

### Root cause (STT)
`Composer.mergeLiveChunk` sent a CUMULATIVE audio blob (t=0 → now) every 1.4s and then tried to dedupe with `endsWith` / `startsWith` string checks. When Whisper drifted even one character (punctuation, casing, or rare word choice) between chunks, NEITHER branch matched and the merge logic appended the entire new transcript onto the previous one — giving 2×, 3×, 4× duplication. When the user finally hit Send, that bloated transcript was persisted as a single message, making it look like "my messages are tripling but Aria's aren't".

### Shipped
- **`Composer.mergeLiveChunk` rewritten**: because we already send the cumulative blob, the server-returned text IS the authoritative full transcript for the whole recording. Trust it — never append. One-liner: `return (incoming || "").trim() || liveTranscriptRef.current`. Kills the triplication at the root.
- **`ShellHeader` rebuilt**: subtitle `COGNITIVE ADAPTIVE OPERATING SYSTEM` restored under the CAOS word-mark. Search was converted from a centered dropdown popover (which the user said "blocks the header/messages") into a compact always-inline input (~96px / "1-inch" wide) glued to the right next to the WCW meter. Collapsed state shows only the magnifying glass; click-to-expand. Click-outside AND Escape now CLEAR the query and close the search (per user's explicit ask).
- **Latency chip plumbing**: `chat_pipeline.run_chat_turn` now wraps `_execute_completion` in `time.perf_counter()` and sets `latency_ms` on both the assistant `MessageRecord` AND the `ReceiptRecord`. Verified via curl: receipts now carry e.g. `latency_ms: 1713` and the `MessagePane` footer green tabular chip (`⏱ 1.7s`) renders on every NEW assistant reply.
- CSS cleanup in `caos-base44-parity-v3.css`: killed the legacy centered popover styles, added `.caos-header-search-inline-*` rules for the new 1-inch input.

### Files touched (all under 400-line soft cap)
- `Composer.js` 294 · `ShellHeader.js` 123 · `caos-base44-parity-v3.css` 266 (was 270, net -4)
- `chat_pipeline.py` 262 (+1) · `artifact_builder.py` 141 (+1) · `schemas/caos.py` 415 (+1)

### Verified
- Screenshots: header collapsed, expanded, and with active query all render correctly; subtitle visible.
- Backend curl: `POST /caos/chat` returns receipt with `latency_ms`, messages endpoint returns assistant with `latency_ms`.

## Next Action Items
- User to verify on `caosos.com` after clicking "Re-deploy changes".
- Phase 4: Complaint Flagging (P1) — awaits user's Resend API key.
- Phase 7: Google Workspace connectors (Gmail / Drive / Calendar).

## Link Persistence + Carousel Expansion (Apr 22, 2026 — evening)

### Shipped
- **Session-scoped link persistence**: added `user_links` collection support with deduped storage (`user_id + session_id + normalized_url`) plus Mongo indexes in `startup.py`.
- **Auto-detect from chat content**: `/api/caos/chat`, `/chat/stream`, and `/chat/multi` now extract prose-embedded URLs via regex and persist them once per session without duplicating on multi-agent fan-out.
- **New links API**: `GET /api/caos/sessions/{session_id}/links` and `POST /api/caos/sessions/{session_id}/links` now serve the Artifacts drawer. Legacy `user_files(kind=link)` records are merged in for backwards compatibility.
- **Artifacts drawer wired**: Links tab now reads the dedicated session links feed, shows source + mention count, supports optional manual labels, and refreshes immediately after manual save.
- **Proactive card expansion**: `MultiAgentMessageGroup` source cards now toggle between preview and expanded states so the selected card reveals full body text instead of staying clipped.

### Verified
- Backend manual verification with seeded auth token: created session, saved manual links, auto-captured two prose URLs via `capture_links_from_message`, and confirmed all links via `GET /api/caos/sessions/{id}/links`.
- Frontend smoke test: authenticated preview loaded, account menu + links drawer mounted, and the links surface rendered under the welcome/tour overlay.

## Updated Next Action Items
- User to verify on `caosos.com` after clicking **Re-deploy changes**.
- P1: Live-turn validation of auto link capture in normal chat and multi-agent mode on the user domain.
- P1: Resend email notifications for support tickets once the Resend API key is provided.
- P2: GitHub token unlock for Swarm repo tools, TTS speed slider, engine-used badge.

## OpenAI Recovery + Mail Action + Time-Aware Continuity (Apr 22, 2026 — late)

### Shipped
- **OpenAI engine recovery**: fixed GPT-5 temperature-param breakage by skipping `temperature` for OpenAI GPT-5 reasoning models that reject non-default sampling controls. Verified live with `POST /api/caos/chat` on `openai:gpt-5.2` returning `OK`.
- **Visible send-failure UX**: when a reply fails, CAOS now preserves the user draft, shows a visible failure state inline, and adds human-readable retry/switch-engine guidance instead of leaving the user hanging.
- **Mail button on assistant replies**: added a `Mail` action on assistant messages that opens the user’s default mail app via `mailto:` with the current thread title as subject and the assistant response as body.
- **Time-aware continuity reinforcement**: continuity anchors now carry summary/seed timestamps into the reinjection packet, and the prompt explicitly instructs Aria to use those timestamps for relative date math after rehydration.

### Verification
- Live backend verification: `POST /api/caos/chat` on `openai:gpt-5.2` succeeded without the old temperature error.
- Frontend verification: mail action visible on assistant reply; forced `/chat/stream` failure preserved the draft and surfaced friendly error copy.
- Backend verification agent passed; frontend verification agent passed.

## Google Workspace Phased Plan (Budget-Friendly)
- **Phase A — Gmail first (smallest useful MVP)**: read inbox summaries + open compose/send flow. Best first connector for immediate user value.
- **Phase B — Drive**: list/search files and pull document metadata/content into CAOS on demand.
- **Phase C — Calendar**: read events, upcoming obligations, and date-aware reminders.
- **Auth / credentials**: use Emergent-managed Google Auth path; no extra Google API key should be needed, but Workspace scopes must be approved when implemented.

## Revised Next Action Items
- P0: User verify the OpenAI fix, Mail action, and failure-state UX on `caosos.com` after the latest redeploy.
- P1: Implement **Google Workspace Phase A (Gmail)** using the integration playbook, then test mailbox read + compose/send flow.
- P1: Resend email notifications for support tickets once the Resend API key is provided.
- P2: Drive connector, Calendar connector, GitHub token unlock for Swarm repo tools, TTS speed slider, engine-used badge.

## Returning-User Onboarding + Latest-Message Landing (Apr 22, 2026 — evening follow-up)

### Shipped
- **Returning-user onboarding fix**: `AuthGate` now checks the server profile (`assistant_name`) before showing the first-run naming modal, so an already-known signed-in user is not prompted again just because local storage is missing in a fresh tab/context.
- **Open to latest message**: `MessagePane` now auto-scrolls to the bottom when a thread loads or the active session changes, so CAOS lands at the newest message instead of the first one.
- **Mail button visibility widened**: regular assistant replies still show `Mail`, and multi-agent synthesis/source cards now also include `Mail` actions so reply export is visible across more response types.

### Verified
- Fresh-tab browser test with `caos_assistant_named` removed: no `Name your AI` modal appeared for the signed-in seeded user.
- Browser test landed at the bottom of the thread (`distance from bottom = 0`).
- Browser test found visible assistant mail buttons; backend sanity check confirmed `assistant_name: "Aria"` exists in the profile payload.

## Updated Immediate Next Actions
- User to click **Re-deploy changes** again before validating on `caosos.com`, since these returning-user / latest-message fixes landed after the prior deploy.
- P1: Gmail Phase A planning/implementation.
- P1: Resend support-ticket emails once the API key is provided.

## Fresh-Load Scroll Regression Fix (Apr 22, 2026 — final pass)

### Root cause
- The thread was not using page scroll on load; it was using the internal `caos-message-scroll` container.
- Earlier fixes were targeting the wrong surface, so fresh loads could still land at the first message even though the app looked authenticated and healthy.

### Shipped
- Added a shell-level post-load scroll routine that directly snaps the internal message container to its full `scrollHeight` after thread hydration and again across a few delayed passes, covering late layout changes.

### Verified
- Long-thread browser regression test passed on preview:
  - `scrollTop: 7598`
  - `scrollHeight: 8426`
  - `clientHeight: 828`
  - `distanceFromBottom: 0`
- Mail button remained visible on assistant replies after the fix.

## Latest Next Actions
- User to click **Re-deploy changes** again before checking `caosos.com`, since this final scroll fix landed after the prior pass.
- P1: Gmail Phase A planning/implementation.
- P1: Resend support-ticket emails once the API key is provided.

## Live Deployed Scroll Parity + Temporal Hydration Anchors (Apr 22, 2026 — late night)

### Root causes found
- **Scroll/layout mismatch:** an older global stylesheet (`App.css`) was still forcing the CAOS shell into a viewport-locked layout (`height: 100vh`, `overflow: hidden`) and making `caos-message-scroll` the active internal scroller with `overflow: auto`. That produced the boxed scrollbar and let older messages disappear behind the composer on the deployed site.
- **Hydration timing ambiguity:** continuity already injected timestamps, but summaries/seeds were stamped mainly by storage time. The prompt also needed a stronger rule that rehydration time is never the event time.

### Shipped
- **Full-page scroll parity**: switched CAOS back to document/page scrolling for chat on desktop-style layouts. The scrollbar is now on the far right of the page/window, while the composer stays fixed at the bottom with enough page padding so older messages remain readable above it.
- **Hybrid scroll logic**: `MessagePane` + `CaosShell` now detect whether the active scroller is the page or an inner container and scroll the correct surface to the latest message.
- **Temporal-anchor fields**: new `thread_summaries` and `context_seeds` now store `source_started_at` and `source_ended_at` so rehydrated facts can carry the original message window, not just the later storage timestamp.
- **Prompt hardening for time-aware hydration**: continuity lines now include `source-window | stored` anchors, memory blocks now include recorded/updated timestamps, and the system prompt explicitly says that reinjection time is not the fact date.

### Verified
- Frontend page-scroll test passed:
  - page scroll active, inner message scroller inactive
  - older messages visible above the fixed composer
  - fresh load still lands at the bottom
  - Mail button still visible
- Backend temporal-anchor test passed:
  - `source_started_at` and `source_ended_at` present on new summaries/seeds
  - continuity/artifacts endpoints serialize successfully
  - recent chat turn still works (`openai:gpt-5.2` tiny reply verified)

## Updated Immediate Next Actions
- User to click **Re-deploy changes** again so the live domain gets the page-scroll parity and temporal-anchor changes.
- P1: Observe whether the new temporal anchors reduce hydration-date confusion in real conversation turns on `caosos.com`.
- P1: Gmail Phase A planning/implementation.

## Scroll Lock-Up + Header Access Fix (Apr 22, 2026 — late-night hotfix)

### Root cause
- Fresh-load positioning to the latest message was working, but wheel input could get swallowed in the live-style page-scroll layout.
- A later stylesheet override in `caos-base44-parity-v3.css` was also resetting the header back to `position: relative`, so once the user landed low in the thread the menu/header could scroll off-screen and feel "gone."

### Shipped
- Simplified duplicate auto-scroll behavior so the page is no longer fighting the user after load.
- Added a wheel-scroll fallback for the page-scrolling shell so manual upward scroll keeps working even when the browser/input path fails to move the page naturally.
- Pinned the shell header/menu so it stays reachable while the user is deep in the thread.
- Preserved bottom-load behavior: CAOS still opens near the latest message, but the page is no longer effectively trapped there.

### Verified
- Fresh load lands near the latest message (`distance from bottom: 0px`).
- Mouse-wheel scroll works from that state (verified movement from `8076px` to `6076px`).
- Header remains fixed and reachable at all scroll positions (`viewport Y ≈ 12px`).
- Composer remains visible and usable.

## Analytics Note
- User asked about platform analytics counts. Clarified that Emergent app analytics can include preview traffic, bots/crawlers, health checks, platform monitoring, and repeated requests — not necessarily real human users.
- User also wants anonymous first-party product analytics later (active users/messages without personal identities). This is **not implemented yet**.


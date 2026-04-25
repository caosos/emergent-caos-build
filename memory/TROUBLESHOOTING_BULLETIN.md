# CAOS Troubleshooting Bulletin

**Last updated:** Apr 25, 2026 (round 3)
**Purpose:** Record of every confirmed bug + the exact fix applied. Reference this BEFORE re-debugging anything in this list — odds are we already solved it.

---

## ✅ FIXED — Apr 24–25, 2026 session

### UI / CSS

| ID | Symptom | Root cause | Fix location | Fix applied |
|---|---|---|---|---|
| F-01 | Settings drawer appeared at the bottom of the page instead of pinned right; hidden behind starfield | Global rule `.caos-shell-root > * { position: relative; z-index: 1 }` (caos-base44-parity.css line 42) was beating drawer-overlay's `position: fixed` | `caos-base44-parity-v3.css` end-of-file | Added explicit `.caos-shell-root > .drawer-overlay { position: fixed !important; z-index: 200 !important }` overrides for drawer/admin/support overlays |
| F-02 | Admin Dashboard button closed the menu but didn't render the dashboard | Missing menu item in `AccountMenu.js`; `ShellHeader` not forwarding `onOpenAdminDashboard` to AccountMenu | `AccountMenu.js`, `ShellHeader.js` | Added `Admin Dashboard · ADMIN` menu entry; wired the prop through |
| F-03 | Bubbles too opaque, hiding starfield/planets behind | Hard alpha values (0.62/0.38) + 6px backdrop-blur halo | `caos-base44-parity-v3.css` | Dropped to `--caos-bubble-opacity: 0.32` CSS var (user-tunable). Removed `backdrop-filter: blur` entirely so stars render sharp |
| F-04 | Massive empty void below last message | THREE separate `.message-scroll { padding-bottom }` rules stacking: 240px, 260px, plus older overrides | `App.css`, `caos-redesign-shell.css`, `caos-base44-parity-v3.css` | All five sources set to `4px`. Recurring offender — be vigilant about new files adding bottom padding |
| F-05 | Background was white during scrolling, washing out everything | `body` had no explicit background; defaulted to white | `index.css` | Set `body { background: #030712 }` (deep space) |
| F-06 | Welcome pre-shell covered stars on the unauthenticated landing | Solid `#05070e` background | `caos-base44-parity-v2.css` | Removed solid background, kept only radial-gradient overlays |
| F-07 | Constellation/planets scrolled WITH content instead of staying fixed | Same offender as F-01 (line 42 rule forcing `position: relative` on every shell child) | `caos-base44-parity.css` | Excluded the constellation layer with `:not([data-testid="caos-constellation-layer"])` |
| F-08 | Voice First Mode opened to a white page | CSS specificity: `.caos-shell-root > *` (0,1,1) beat `.vfm-overlay` (0,1,0); overlay rendered inline-flow at z-index 1 | `VoiceFirstMode.css` | Added `!important` on `position: fixed`, `inset: 0`, `z-index: 400` |
| F-09 | Engine chip on a past reply showed "Gemini" but bottom selector said "Claude" — looked contradictory | Two different concepts (engine that answered vs engine for next reply) labeled identically | `EngineChip.js` | Bottom chip now reads "engine for next reply" + tooltip explaining past chips show actual answerer |

### Auth / Session

| ID | Symptom | Root cause | Fix location | Fix applied |
|---|---|---|---|---|
| F-10 | Logout immediately re-authenticated | Two stacking bugs: (a) `delete_cookie()` missing `httponly=True` so attribute mismatch made browser keep the cookie; (b) only the cookie's session row was deleted, but multiple rows accumulate per user from repeated logins | `auth.py` `/auth/logout` route | Removed `Depends(require_user)` so partially-expired sessions can still log out. Now nukes ALL sessions for the user. Doubled-up cookie clear (`delete_cookie` + explicit expired `set_cookie`) |
| F-11 | "Invalid state parameter" 404 on Google OAuth | Upstream issue at `demobackend.emergentagent.com` (state cookie bound to that domain, not yours) | N/A — not your code | Documented; users should retry in incognito or whitelist `*.emergentagent.com` for cross-site cookies |

### Backend / Data

| ID | Symptom | Root cause | Fix location | Fix applied |
|---|---|---|---|---|
| F-12 | "Admin access required" 403 even for admin users | `admin_dashboard.py` queried `user_profiles.is_admin` separately while `admin_docs.py` used the simpler `user.get("is_admin")` from the auth-resolved dict — inconsistent | `admin_dashboard.py::require_admin` | Unified to `user.get("is_admin") or user.get("role") == "admin"` |
| F-13 | Tier distribution showed impossible percentages (e.g., 857.1%) | Total users came from `users` collection but tier sum came from `user_profiles` (which had more rows from dangling profiles) | `admin_dashboard.py` `/dashboard/metrics` | Clamp + rescale tier counts so they never exceed total_users; backfill untiered as `free` |
| F-14 | WCW meter stuck at `200k` regardless of model | Hardcoded `wcw_budget = 200000` in chat_pipeline | `chat_pipeline.py`, new `model_catalog.py` | Pulls from per-model context window (1M Claude/Gemini, 400k GPT-5.2, etc.) |
| F-15 | "8 validation errors for ChatResponse" wall when chat blocked | Quota-exceeded early return used WRONG field names (`content`, `role`, `token_receipt`) instead of schema (`reply`, `assistant_message`, `receipt`) | `chat_pipeline.py` line 60 | Rewrote with correct schema; also auto-skipped quota check for admin users |
| F-16 | History truncated to 2.2k tokens despite 1M-context models | `history_token_budget = 2200` hardcoded default | `chat_pipeline.py` | Now `max(payload.history_token_budget, int(model_ctx * 0.70))` — scales with active model |

### Voice / STT

| ID | Symptom | Root cause | Fix location | Fix applied |
|---|---|---|---|---|
| F-17 | STT hallucinations / word doubling | Streaming chunks confused Whisper | `Composer.js` STT logic (earlier session) | Rewrote to single-blob Base44-style |
| F-24 | STT "stop" button had visible latency before processing started (was OPEN-04) | `recorder.stop()` is async — UI gave no feedback for ~500ms | `Composer.js::stopRecording` | `setRecording(false)` + `setTransientStatus("Processing transcription…")` fire IMMEDIATELY before `recorder.stop()`. Verified live. |

### Engine routing / Errors / Memory

| ID | Symptom | Root cause | Fix location | Fix applied |
|---|---|---|---|---|
| F-18 | Engine toggle silently overridden to Gemini whenever the session had any image attachment, even old ones (was a hidden bug — user reported "engine toggle defaults to Gemini") | `useCaosShell.js:311-318` force-set `effectiveProvider="gemini"` when ANY image existed in `files` for that session_id | `useCaosShell.js` | Removed silent override. Now shows a status hint "only Gemini can see image contents" when user is on Claude/GPT with images attached. User's choice always wins. Verified live. |
| F-19 | Sanitizer 200-char prefix dedup deleted legitimate divergent history (was OPEN-02 — Aria's ticket) | `context_engine.py:117` keyed dedup by `(role, normalized[:200])` — two messages with the same opener but different endings collapsed into one | `context_engine.py::sanitize_history` | Replaced with full-content exact match `(role, normalized_content)`. Verified with a Python unit-style test (3 messages, only 1 dup, exactly 1 removed = PASS). |
| F-20 | "8 validation errors for ChatResponse" stack trace appearing inside the chat bubble on engine failure (round-1 user complaint, screenshots 3 & 4) | Backend `chat_stream` SSE error event yielded raw `str(error)` to client; frontend rendered it verbatim in the failure bubble | `routes/caos.py::chat_stream`, `useCaosShell.js` catch handler, `caos-base44-parity.css` | Three layers of defense: (1) backend maps known patterns ("validation error", "rate limit", "timeout", "api key" → "401") to friendly text and never leaks raw stack traces, (2) frontend recognizes Pydantic-style messages and trims to ≤200 chars, (3) `.message-error-note` CSS clamps to 5 lines + 7.5em max-height. |
| F-21 | Constellation/stars not visible on the unauthenticated welcome page (was OPEN-06) | `<ConstellationLayer />` was only mounted inside `<CaosShell />` — only rendered post-auth | `App.js`, `CaosShell.js` | Hoisted `<ConstellationLayer />` to App root (above `<BrowserRouter>`) so it renders behind LoginScreen too. Removed the duplicate mount inside CaosShell. Verified live (Saturn, Mars, Venus, constellation lines visible behind the Welcome cards). |
| F-22 | Render crash → entire app whitescreens (was OPEN-07) | No frontend error boundary; any sync render exception killed the whole UI | `CaosErrorBoundary.js` (new), `App.js` | Added `<CaosErrorBoundary />` class component wrapping the entire `<BrowserRouter>` tree. Catches sync render exceptions, shows a dark recovery screen with "Reload CAOS" + "Clear local state" buttons. Logs full error to console for debugging. |
| F-23 | Login routed to a blank "New Thread" stub instead of resuming the user's last conversation (was OPEN-01) | `useCaosShell.js` hydrate effect picked `foundSessions[0]` blindly. When user creates "New Thread" but doesn't send a message, that empty stub becomes most-recent-by-`updated_at` and was the auto-loaded session. Multiple users had 7+ such empty stubs piled at the top of their list. | `useCaosShell.js::hydrate` effect | Walks the (already-sorted-desc) sessions list and picks the first one with a populated `last_message_preview`. Falls back to `[0]` only if every session is empty. Status banner now reads "Resumed your last conversation: <title>". Verified live with seeded user (1 empty + 1 populated; correctly resumed populated). |
| F-25 | Search drawer results appeared at the LEFT-BOTTOM of the screen (under the AccountMenu) instead of top-right next to the search input (was OPEN-05) | `caos-base44-parity.css:42` set `position: relative; z-index: 1` on every direct child of `.caos-shell-root` (except constellation), silently overriding `.thread-search-panel`'s `position: fixed; right: 20px; top: 88px`. The drawer was dumped into the document flow at the bottom-left. | `caos-base44-parity.css` | Broadened the `:not()` exclusion list to also exempt `.thread-search-panel`, `.inspector-panel`, `.previous-threads-panel`, `.drawer-overlay`, `.command-footer`, `.admin-dashboard-overlay`. Added a code comment documenting the trap so future fixed panels added as direct children get whitelisted. Verified live: drawer reports `x=1545, y=88, w=340` after typing — exactly top-right where the input is. Also relabeled the threads-panel search input "Search across all threads…" so its scope is clear. |
| F-26 | "Log out" button → user immediately logged back in (round-3 user complaint) | TWO stacked bugs: (a) `.caos-header` was at `z-index:1` same as `.caos-shell-grid` — grid wins source order, so the AccountMenu dropdown's lower half was painted-over by WelcomeHero cards; clicks at "Log Out"'s coordinates resolved to a card behind it, the menu's outside-handler closed it, and the user thought "the menu blinked but nothing happened"; (b) `onLogOut` referenced `${API}/auth/logout` but `API` was NEVER imported into `CaosShell.js` — the URL evaluated to `undefined/auth/logout`, axios threw on the malformed URL, the empty `try{}catch{}` swallowed it, AND the code never reached the redirect line either. Cookie + DB session stayed alive, next `/auth/me` call auto-renewed, user appeared "logged right back in." | `caos-base44-parity.css` (header z-index 60), `CaosShell.js` (`import { API }`, static axios, full client-side cookie/localStorage wipe, `console.error` on failures) | **Verified end-to-end live**: network capture shows `/api/auth/logout` actually fires, cookies count drops 1→0, DB query post-logout shows `user_sessions.count({token})=0` AND `user_sessions.count({user_id})=0` (backend nukes ALL sessions for the user). |

---

## ❌ KNOWN OPEN BUGS (NOT yet fixed)

| ID | Severity | Bug | Suspected fix |
|---|---|---|---|
| OPEN-03 | P1 | WCW meter stagnates on engine failure — `lastTurn` doesn't update when the stream errors, so the meter shows the last-successful value | In `useCaosShell.js` failure handler, also fetch the latest receipt or update `lastTurn.wcw_used_estimate` from a quick `/caos/sessions/{id}/receipts/latest` call | Low impact — only affects display after errors |
| OPEN-08 | P3 | "Log out everywhere" not exposed in UI | Backend already nukes all sessions for the user on logout. Add an explicit "Log out from all devices" checkbox in the AccountMenu, plus a Profile-drawer view of active sessions per device with revoke buttons | Nice to have for security UX |

---

## ⚠️ RECURRING OFFENDERS (whack-a-mole watch list)

1. **`.caos-shell-root > * { position: relative; z-index: 1 }`** in `caos-base44-parity.css` — causes drawer/overlay/constellation z-index issues. Already excluded constellation, search drawer, inspector, previous-threads, drawer-overlay, command-footer, admin-dashboard, AND caos-header. **If you add a new fullscreen overlay or a fixed-position panel as a direct child of `.caos-shell-root`, you MUST add it to the `:not(...)` exclusion list** — otherwise `position: fixed` is silently overridden and the panel lands in the document flow somewhere weird (top-right pin → bottom-left dump).
2. **Multi-file CSS for `.message-scroll`, `.caos-main-column`** — five separate sources have padding rules. Always grep all CSS files when fighting spacing bugs.
3. **`record_session` creates new row per login** — over time `user_sessions` accumulates duplicates per user. Logout nukes them all, but consider adding a UNIQUE index on `(user_id, session_token)` and using upsert.
4. **Dynamic `await import("…")` inside event handlers** — if the chunk fetch fails (slow CDN, midnight blip, code-split race), the await blocks forever, the catch never fires, and code below the await is unreachable. Prefer static imports for anything in user-interaction paths (the F-26 logout bug was this exact trap with a `try{}catch{}` masking it).
5. **`${API}` references inside `CaosShell.js`** — `API` is exported from `@/config/apiBase` and MUST be imported explicitly. Several handlers historically referenced `${API}` while relying on it being in scope from a sibling file that bundles them together. It isn't. Always check imports when adding new endpoint calls.
6. **Empty "New Thread" stubs** — clicking "New Thread" without sending a message creates a session with `last_message_preview=""` and `updated_at=now()`. Multiple users have piled up 7+ such stubs at the top of their list. Login routing now skips empties and resumes the most recent populated session, but a future polish item is to either dedupe at create time or auto-archive empty stubs older than 24h.

---

## 🚨 PROTECTED — DO NOT TOUCH

- **STT logic in `Composer.js`** — single-blob recording. DO NOT re-add streaming chunks (caused hallucinations).
- **Rate limit middleware** — currently disabled. If re-enabling, MUST be added AFTER `CORSMiddleware` in `server.py` or 502s on preflight.
- **Cookie attributes** in `set_cookie` and `delete_cookie` MUST match: `httponly=True, secure=True, samesite="none", path="/"`. Any mismatch → cookie persists.
- **`/app/memory/test_credentials.md`** — keep current; testing agent reads it.

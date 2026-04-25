# CAOS Troubleshooting Bulletin

**Last updated:** Apr 25, 2026
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

---

## ❌ KNOWN OPEN BUGS (NOT yet fixed)

| ID | Severity | Bug | Suspected fix |
|---|---|---|---|
| OPEN-01 | P1 | Login routes to fresh empty thread instead of resuming last session | `useCaosShell` doesn't auto-load most-recent session_id on mount. Add a useEffect that picks the latest non-flagged session for the user and sets it active |
| OPEN-02 | P1 | Sanitizer 200-char dedup deletes legitimate history (Aria's ticket) | Replace 200-char prefix hash with full-content hash + raise the signal floor; OR keep prefix hash but also check timestamp delta |
| OPEN-03 | P1 | WCW meter stagnates due to stale context receipts (Aria's ticket) | Receipts caching too aggressively — invalidate on each turn, force re-compute |
| OPEN-04 | P2 | STT "stop" button has visible latency before processing starts | `recorder.stop()` is async; add immediate UI state change to "Processing…" before awaiting |
| OPEN-05 | P2 | Two redundant search bars on the same page; thread search results render in wrong drawer | Audit the search components — consolidate `ThreadSearch` and `GlobalSearch` into one `Cmd+K` palette |
| OPEN-06 | P2 | Constellation layer not rendered on unauthenticated welcome page | Move `<ConstellationLayer />` mount up to App.js (above AuthGate) so it shows regardless of auth state |
| OPEN-07 | P3 | Frontend has no error boundary — render crash white-screens entire app | Wrap `<CaosShell />` in a `<CaosErrorBoundary />` with fallback UI |

---

## ⚠️ RECURRING OFFENDERS (whack-a-mole watch list)

1. **`.caos-shell-root > * { position: relative; z-index: 1 }`** in `caos-base44-parity.css` — causes drawer/overlay/constellation z-index issues. Already excluded constellation layer; if you add a new fullscreen overlay, exclude it via `:not([data-testid="..."])`.
2. **Multi-file CSS for `.message-scroll`, `.caos-main-column`** — five separate sources have padding rules. Always grep all CSS files when fighting spacing bugs.
3. **`record_session` creates new row per login** — over time `user_sessions` accumulates duplicates per user. Logout now nukes them all, but consider adding a UNIQUE index on `(user_id, session_token)` and using upsert.

---

## 🚨 PROTECTED — DO NOT TOUCH

- **STT logic in `Composer.js`** — single-blob recording. DO NOT re-add streaming chunks (caused hallucinations).
- **Rate limit middleware** — currently disabled. If re-enabling, MUST be added AFTER `CORSMiddleware` in `server.py` or 502s on preflight.
- **Cookie attributes** in `set_cookie` and `delete_cookie` MUST match: `httponly=True, secure=True, samesite="none", path="/"`. Any mismatch → cookie persists.
- **`/app/memory/test_credentials.md`** — keep current; testing agent reads it.

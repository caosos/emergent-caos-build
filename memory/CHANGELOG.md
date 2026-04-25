# CAOS Changelog

## 2026-04-25 — Tier 1 critical bug sweep

### 🔴 Bug fixes (P0 / P1)
- **[ENGINE-01]** Removed silent auto-override that hijacked the user's engine choice to Gemini whenever the session had any image attachments. The user-selected engine (Claude / GPT / Gemini) is now respected on every turn. When the session has images and a non-Gemini engine is active, a one-line hint is shown in the status row instead of forcing a switch. *Files: `useCaosShell.js`*
- **[SANITIZER-01]** Replaced the 200-character prefix dedup key with a full-content exact match. The previous heuristic collapsed two divergent messages that started with the same 200 chars into one, silently destroying real history. Verified with a unit-style test (3 messages, only 1 dup, exactly 1 removed). *Files: `context_engine.py`*
- **[ERROR-UI-01]** The 8-line Pydantic validation stack trace that appeared inside the chat bubble on engine failure is now sanitized at three layers: (1) backend `chat_stream` SSE error event maps known patterns to friendly text and never leaks `str(error)` raw, (2) frontend `useCaosShell.js` catch handler trims long traces and recognizes Pydantic-style messages, (3) the `.message-error-note` CSS clamps to 5 lines + 7.5em max-height as a final guardrail. *Files: `routes/caos.py`, `useCaosShell.js`, `caos-base44-parity.css`*

### 🟠 UI polish (P2)
- **[STT-01]** STT stop button now reflects "Processing transcription…" instantly on click, before the async `recorder.stop()` round-trip resolves. Removes the half-second of dead air the user reported. *Files: `Composer.js`*
- **[CONSTELLATION-01]** `<ConstellationLayer />` is now mounted at the App root (above `<AuthGate />`) so the drifting stars + planets appear on the welcome / login screen as well as the authed shell. Removed the duplicate mount inside `<CaosShell />`. *Files: `App.js`, `CaosShell.js`*
- **[ERROR-BOUNDARY-01]** Added `<CaosErrorBoundary />` class component that catches any synchronous render crash and shows a dark-themed recovery screen with "Reload CAOS" and "Clear local state" actions instead of white-screening. Wraps the entire `<BrowserRouter>` tree. *Files: `CaosErrorBoundary.js` (new), `App.js`*
- **[SEARCH-LABEL-01]** Renamed the Previous-Threads-panel search input from "Search all messages..." to "Search across all threads…" to make its scope (cross-thread) clearly distinct from the header's "Search this thread" pill. *Files: `PreviousThreadsPanel.js`*

### 🧪 Testing performed
- Backend Python unit-style verification of `sanitize_history` with overlap-prefix messages → PASS.
- Smoke screenshot of pre-login welcome screen → constellation + planets visible behind gradient. PASS.
- Backend health curl `/api/` → 200 OK.
- Frontend lint + Python ruff → all clean.
- *Per user directive: NO `testing_agent_v3_fork` invoked. Manual verification only.*

### 🟡 Deferred (not in this sweep)
- WCW meter staleness on engine failure — minor; only affects display after errors.
- Login-routes-to-empty-thread — codepath already picks `foundSessions[0]` after backend sort `updated_at DESC`. Couldn't reproduce in code review; deferring until the user reports a fresh case.
- Retry button on failure notice — needs `MessagePane.js` refactor; out of sprint scope.
- Two-search-bar consolidation — labels disambiguated for now; unifying into a single command-palette is a Tier-2 polish item.

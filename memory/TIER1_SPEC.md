# Tier 1 — Critical Bug Fix Spec

**Goal:** Stop the 7 user-facing breakages currently shipping. NO new features. NO polish.
**Budget cap:** 60 credits (~30 tool calls). If anything blows past 50 credits, STOP and ask user.
**Reference:** `/app/memory/TROUBLESHOOTING_BULLETIN.md` for context on already-fixed bugs.

---

## Bugs to fix (in this order)

### 1. OPEN-01 — Login routes to empty new thread instead of last session (P1)
**Symptom:** User signs in → lands on a blank thread. Their previous conversation is one click away in Threads but they shouldn't have to find it.
**Suspected root:** `useCaosShell.js` doesn't pick a default `currentSessionId` on mount.
**Fix sketch:** In the user-bootstrap effect, after sessions list is loaded, set the active session to the most recent non-flagged session for that user. Skip if there are zero sessions (then create a new one as today).
**Test:** Login → should land on last conversation.
**Estimate:** 4–6 tool calls

### 2. OPEN-04 — STT "stop" button latency (P2 but trivial)
**Symptom:** Click the mic-stop button, half-second of dead air, then UI updates.
**Suspected root:** UI state change happens after the `await recorder.stop()` promise resolves.
**Fix sketch:** In `Composer.js` STT stop handler, set UI state to "Processing…" *immediately* before awaiting `recorder.stop()`.
**Test:** Click stop → "Processing" chip should appear instantly.
**Estimate:** 2–3 tool calls

### 3. OPEN-06 — No constellation on welcome / login page (P2)
**Symptom:** Pre-login page is plain — no stars/planets behind it.
**Suspected root:** `<ConstellationLayer />` is mounted inside `<CaosShell />` which only renders after auth.
**Fix sketch:** Move ConstellationLayer mount up to `App.js` (above `<AuthGate />`) so it renders globally. Verify z-index still puts it behind everything.
**Test:** Logged-out → welcome page now has drifting stars.
**Estimate:** 3–4 tool calls

### 4. OPEN-07 — Frontend has no error boundary (P3 but easy)
**Symptom:** Any render crash white-screens the whole app — user has no idea what happened.
**Fix sketch:** Create `<CaosErrorBoundary />` (class component with `componentDidCatch`). Wraps `<CaosShell />` and `<AuthGate />` in App.js. On error: show a dark-themed fallback "Something glitched. Click here to reload" with the error message.
**Test:** Throw a test error in a component → fallback shows instead of white screen.
**Estimate:** 4–5 tool calls

### 5. OPEN-02 — Sanitizer 200-char dedup deletes history (P1, from Aria's ticket)
**Symptom:** Long conversations lose middle messages. Aria sometimes "forgets" something said earlier.
**Suspected root:** `sanitizer_service.py` (or wherever sanitize_history lives) uses first 200 chars as a hash key. Two messages starting similarly get deduped.
**Fix sketch:** Replace 200-char prefix hash with full-content SHA-256 hash. Keep the dedup but make it exact-match only, not fuzzy.
**Test:** Send 5 messages that all start with the same 50 words but diverge after — all 5 should remain in history.
**Estimate:** 4–6 tool calls

### 6. OPEN-03 — WCW meter stagnates from stale receipts (P1, from Aria's ticket)
**Symptom:** WCW meter freezes at an old value instead of updating after each turn.
**Suspected root:** `context_engine.py` or chat_pipeline returns the same receipt object after recompute even when stats changed.
**Fix sketch:** Force `receipt` to be re-built from scratch each turn (not mutated from prior). Verify `wcw_used_estimate` reflects current `compressed` history token count.
**Test:** Send 3 messages → WCW number should grow each time (or shrink if compression kicks in).
**Estimate:** 5–7 tool calls

### 7. OPEN-05 — Two redundant search bars / search results in wrong drawer (P2, from Aria's ticket)
**Symptom:** Search bar appears twice on screen. Results show in the wrong panel.
**Suspected root:** Both `ThreadSearch` and a global search are mounted; results route to the wrong drawer.
**Fix sketch:** Identify the duplicate. Hide the secondary one. Verify results render in the same drawer that owns the input.
**Test:** Open the page → only one search bar visible. Type a query → results in the same drawer.
**Estimate:** 4–6 tool calls

---

## Total estimate

**~30 tool calls = ~60 credits.** If any single bug above blows past 10 tool calls, STOP and ask.

## After Tier 1: ship checkpoint

1. Smoke test with one screenshot
2. Update `TROUBLESHOOTING_BULLETIN.md` with new fixes (move OPEN-* to FIXED)
3. `finish` tool with crisp summary
4. User redeploys `caosos.com`

## Workflow guardrails for the agent

- **DO NOT** call `testing_agent_v3_fork` — user is credit-sensitive
- **DO NOT** rewrite working code; surgical search_replace only
- **DO** check `TROUBLESHOOTING_BULLETIN.md` before any debugging
- **DO** run lint after each batch of edits
- **DO** redeploy reminder at the end (custom domain caosos.com)

## After Tier 1 → Tier 2 plan

Polish bundle (~80 credits, NEW SESSION):
- H1 Budget alert
- H2 Personal spend view
- H3 Scrollbar styling
- H8 Syntax highlighting in code blocks
- H9 Error drill-down
- I6 (already part of Tier 1: error boundary)

Tier 3 = Daily driver (~250 credits): Tier 2 + Gmail Phase A + Lane memory vault
Tier 4 = Commercial (~600 credits): Tier 3 + Stripe + remaining connectors

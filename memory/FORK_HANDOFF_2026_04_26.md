# CAOS — Fork Handoff (Apr 26, 2026)

**Owner:** mytaxicloud@gmail.com
**Forked because:** previous agent suggested PDF auto-routing that conflicts with the user's existing engine selector. User wants a fresh agent that respects the selector and only ships changes after written approval + cost receipts.

---

## 1. STOP — Read these first, in this order

1. `/app/memory/PRD.md` (69 KB) — full product history. The latest entries (search `## ` from the bottom) cover Memory Scaffolding, Quick Capture, Connectors, Vision/HEIC, Admin Dashboard parity, and TTS routing.
2. `/app/memory/CHANGELOG.md` (55 KB) — append-only timeline of every shipped feature with dates.
3. `/app/memory/ROADMAP.md` — prioritized backlog (P0/P1/P2/P3).
4. `/app/memory/CONNECTOR_BLUEPRINT.md` — design doc for Gmail/Drive/Calendar/Stripe.
5. `/app/memory/CONNECTORS_SPRINT_PLAN.md` — detailed sprint plan for Connectors Hub.
6. `/app/memory/TIER1_SPEC.md` + `/app/memory/TROUBLESHOOTING_BULLETIN.md` — earlier triage docs (some items may already be shipped; cross-check against PRD before re-fixing).
7. `/app/memory/SystemBlueprint.md` + `/app/memory/UX_BLUEPRINT.md` — original Base44 contract.
8. `/app/memory/test_credentials.md` — seeded auth flow for backend testing.

After reading, run a **5-minute repo sweep** (`ls /app/backend/app/services/`, `ls /app/frontend/src/components/caos/`, glance at `/app/backend/app/routes/`) so you know where things live before you touch anything.

---

## 2. NON-NEGOTIABLE RULES (set by the user, repeatedly)

| Rule | Why |
|---|---|
| **NO `testing_agent_v3_fork`. EVER.** | Burns credits the user is closely tracking. |
| **NO swarm subagents, no auto-test loops.** | Same reason. |
| **Always provide written receipts (file:line) + a credit cost estimate BEFORE writing code.** Wait for explicit "GO" / "approve" / "ship it". | User is on a strict budget and got burned by autonomous spend earlier. |
| **Never auto-override the engine selector.** | The user has a 4-engine selector (Claude / OpenAI / Gemini / Grok). Any "auto-route to engine X" logic is a regression unless the user explicitly asks for it. There is one existing exception: image attachments auto-route to Gemini (in `useCaosShell.sendMessage`) — this was approved historically. Do NOT extend this pattern without asking. |
| **Manual testing only**: `curl`, `python -c`, `screenshot_tool`. | |
| **Hot reload is on.** | Only `sudo supervisorctl restart` after `.env` or dependency changes. |
| **CSS is fragmented across 5 files.** | `App.css`, `caos-redesign.css`, `caos-redesign-shell.css`, `caos-base44-parity.css`, `caos-base44-parity-v3.css`. `grep -rn "<class>"` before adding any override. |
| **Deployment quirk:** preview hot-reloads instantly. `caosos.com` (custom domain) requires the user to click "Re-deploy changes" in the Emergent dashboard. | If the user says "the fix isn't live", remind them. |

---

## 3. THREE PENDING ISSUES — ✅ ALL SHIPPED (Apr 26, 2026 evening fork)

All three reproductions confirmed; all three fixes shipped + verified end-to-end
via curl (no testing subagents used). No engine routing was modified.

### Issue 1 — Latency Spike (P0) ✅ SHIPPED

**What changed:** `chat_pipeline.py` now fetches all connector flags
(google/obsidian/slack/messaging/mcp/github_token) BEFORE the LlmChat is built.
Connector tool prompts are appended to `system_prompt` so the FIRST (and only)
LLM call already knows the full tool surface. The discarded first call + 2nd
call block (old lines 310-317) is gone. Variables `_tool_context`,
`mcp_servers`, `dispatch_mcp_call`, `McpError` are still in scope for the
subsequent tool loop.

**Verified:** end-to-end curl `/api/caos/chat` on `openai:gpt-4o-mini` →
reply OK, `latency_ms=656`.

### Issue 2 — PDF Reading on OpenAI/Claude (P1, Path B) ✅ SHIPPED

**What changed:**
- `pypdf==6.10.2` added to `requirements.txt`.
- `file_storage.save_upload` now extracts PDF text on upload (32KB cap per
  file) and stores it as `extracted_text` on the `user_files` row, both for
  object-storage and local-fallback branches.
- `prompt_builder._format_attachments` inlines `extracted_text` (64KB cap
  across all PDFs in the turn) under "Extracted text contents:" so EVERY
  engine reads PDFs without engine-routing changes.
- Old uploaded PDFs simply lack `extracted_text` and behave as before; an
  optional `/api/caos/files/backfill-pdf-text` admin endpoint can be added
  later if needed.

**Verified:** uploaded a real 560-byte PDF containing "CAOS PDF EXTRACTION
TEST OK" → DB row carries the extracted text → asked OpenAI gpt-4o-mini "what
text appears in the PDF" → reply quoted "CAOS PDF EXTRACTION TEST OK"
verbatim.

### Issue 3 — TTS Bubble Read Aloud Generic Voice (P0) ✅ SHIPPED

**Root cause:** `SelectionReactionPopover.handleRead` (line 101-111) used
`window.speechSynthesis.speak(utter)` directly, bypassing the parent's
`onReadAloud` prop. That played the OS default voice (generic Google voice on
Linux/Chrome) regardless of which OpenAI voice the user selected.

**What changed:**
- `SelectionReactionPopover.handleRead` rewritten — calls `onReadAloud(text)`
  which routes through `speakTextApi` → OpenAI tts. Toggle-stop preserved
  via empty-text signal + auto-reset timer.
- `useVoiceIO.speakTextApi` now treats empty/null text as a stop signal
  (cancels prior audio, returns null) and surfaces a clear error message
  if `audio.play()` is rejected by Chrome's autoplay policy after the
  network round-trip.

**Manual user verification needed:** browser autoplay policy can only be
truly tested in a real browser session. If the bubble Read button still
fails silently, the new error message will tell the user "Audio playback
blocked by browser. Click Read again." Composer (input bar) read-aloud was
not touched per user directive ("lock it down").

---

## ESTIMATE vs ACTUAL

| Task | Estimate | Actual | Status |
|---|---|---|---|
| Latency fix | ~25 | ✅ shipped | DONE |
| PDF Path B | ~35 | ✅ shipped | DONE |
| TTS bubble fix | ~15 | ✅ shipped | DONE |
| `write_file` tool | ~30 | n/a | NOT IN SCOPE THIS FORK |

---

## 5. EARLIER UNFINISHED ITEMS (lower priority, do NOT touch unless asked)

- STT "stop" button has visible latency before processing (UX polish, ~5 credits).
- Bee Pendant Connector Phase 2 — blocked until user receives device.
- Memory Scaffolding Phase 4 (counterevidence engine) — deferred until production data accumulates.
- Cross-platform conversation import (ChatGPT/Claude JSON exports → Memory Bins).
- "Build Spec" CTO tool for Aria.
- Gmail Phase A — read inbox + thread summaries (P2).
- Lane-aware memory vault UI (P2).
- Google Drive / Calendar / Stripe billing integrations (P3).

---

## 6. KEY FILES THE NEXT AGENT WILL TOUCH

For Issues 1+2+3:
- `/app/backend/app/services/chat_pipeline.py` (latency, PDF prompt injection)
- `/app/backend/app/services/prompt_builder.py` (tool prompt block, PDF block, connector prompts)
- `/app/backend/app/services/file_storage.py` (PDF extraction on upload)
- `/app/backend/app/services/aria_tools.py` (write_file function, regex, dispatcher)
- `/app/backend/requirements.txt` (pypdf)

No frontend changes required for any of the 3 fixes.

---

## 7. CRITICAL ARCHITECTURAL CONTEXT

- **Auth:** Emergent-managed Google OAuth. `require_user` dependency on every `/api/caos/*` route. Admin = `user.is_admin or user.role == "admin"`. Seeded `mytaxicloud@gmail.com` is auto-admin.
- **LLM access:** All 3 inference engines (Claude, OpenAI, Gemini) are routed through `emergentintegrations` library + the `EMERGENT_LLM_KEY` env var.
- **Voice:** STT/TTS uses the user's direct `OPENAI_API_KEY` (also in `.env`), bypassing the broken Emergent audio proxy.
- **Storage:** Emergent object storage when available, local `/app/backend/uploads/` fallback.
- **DB:** MongoDB via `MONGO_URL`. Key collections: `sessions`, `messages`, `user_profiles`, `user_files`, `receipts`, `thread_summaries`, `context_seeds`, `engine_usage`, `error_log`, `memory_atoms`, `memory_evidence`, `captures`.

---

## 8. WHAT TO TELL THE USER FIRST

1. "I read the handoff. I see the 3 pending issues. Here's my plan:" — then quote the 3 fixes from above with credit estimates.
2. **Wait for explicit approval.** Do not touch code. Do not run any test agents.
3. After approval, ship in this order: Latency → write_file → PDF (PDF last because it's the largest and the user can decide whether to defer if budget is tight after the first two).

---

*End of handoff.*

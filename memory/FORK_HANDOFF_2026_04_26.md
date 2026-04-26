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

## 3. THREE PENDING ISSUES — investigated, NOT yet fixed

The previous agent investigated all 3 and produced receipts. **No code was written.** User stopped the agent because the PDF approach was wrong. Here's the corrected breakdown:

### Issue 1 — Latency Spike (P0, ~25 credits to fix)

**Root cause (confirmed via code read):** `/app/backend/app/services/chat_pipeline.py` lines **310-317**.
When ANY connector is enabled (Google / Obsidian / Slack / Twilio / Telegram / MCP), the pipeline runs the LLM **twice** per turn:

```python
# Line ~261 — first LLM call
llm_response = await chat._execute_completion(pending_messages)
reply = await chat._extract_response_text(llm_response)

# Lines 287-309 — build connector tool prompts (Google/Obsidian/Slack/Twilio/Telegram/MCP)
extra_prompt_chunks: list[str] = []
if google_connected: ...
if obsidian_connected: ...
# ...etc

# Lines 310-317 — SECOND LLM call (this is the bug)
if extra_prompt_chunks:
    await chat._add_user_message(pending_messages, UserMessage(text="\n\n".join(extra_prompt_chunks)))
    llm_response = await chat._execute_completion(pending_messages)
    reply = await chat._extract_response_text(llm_response)
```

The first reply is silently discarded. This costs **2× tokens and ~2× latency** for every turn after a connector is hooked up.

**Fix:** Move the connector tool prompts INTO the initial `system_message` string built by `build_system_prompt_from_sections` (in `prompt_builder.py`). Then the first (and only) LLM call already knows the full tool surface. Remove the `if extra_prompt_chunks: ... _execute_completion(...)` block entirely.

**Secondary win (optional, ~+10 credits):** parallelize the 6 sequential DB awaits before the LLM call (`sessions list`, `summaries`, `seeds`, `workers`, `global_info`, `attachments`) using `asyncio.gather`. ~150-300 ms additional savings on long threads.

**Test plan:** authenticated curl `/api/caos/chat` with a session that has Google connected, before vs after. Compare `latency_ms` in the receipt. Should drop ~50%.

---

### Issue 2 — PDF Reading Regression (P1, ~35 credits, Path B confirmed)

**Root cause:** `/app/backend/app/services/chat_pipeline.py` lines **205-238** only attach **image** MIME types to OpenAI/Claude as `ImageContent`. PDFs are passed only to Gemini via `FileContentWithMimeType` (Gemini-only API). On OpenAI/Claude, the PDF only appears as a filename string in the system prompt — Aria can't read its contents.

**DECIDED APPROACH (do NOT change):** **Path B — server-side PDF text extraction.**
- Path A (auto-route to Gemini) was suggested by the previous agent and **rejected by the user** because it conflicts with the explicit engine selector. Don't propose it again.
- Path B does NOT touch routing. The user's selector keeps doing exactly what they told it.

**Implementation plan for Path B:**
1. `pip install pypdf` and freeze into `requirements.txt`.
2. In `/app/backend/app/services/file_storage.py::save_upload()`, after the bytes are read, if `mime_type == "application/pdf"`, run `pypdf.PdfReader(io.BytesIO(raw))` and concatenate page text. Store as `extracted_text` (cap at ~32 KB) on the file metadata dict.
3. In `chat_pipeline.py::run_chat_turn`, after `attachment_docs` is fetched, build a new prompt block: for any attachment with `extracted_text`, inject it under a new "PDF text contents" section in the system prompt. Cap total injected text at ~64 KB across all PDFs.
4. In `prompt_builder.py::_format_attachments`, append the extracted text after the filename line for any item that has it.
5. Migrate existing PDFs: optional one-shot endpoint `POST /api/caos/files/backfill-pdf-text` (admin-gated) that re-extracts text for already-uploaded PDFs.

**Test plan:** upload a 5-page PDF via curl, hit `/api/caos/chat` with `provider=openai`, verify the reply references content from page 3 of the PDF.

---

### Issue 3 — Missing `write_file` Tool for Aria (P1, ~30 credits)

**Root cause:** `/app/backend/app/services/aria_tools.py` only has read-only tools. Aria can't programmatically save formatted reports (e.g., the user's "Finance Tracker" workflow).

**Decided approach:** Add a new sandboxed tool marker:
```
[TOOL: write_file name=<filename.md> content=<text>]
```

**Implementation plan:**
1. New function `aria_write_file(name, content, user, session_id)` in `aria_tools.py`:
   - Validate filename: no `/`, no `..`, max 120 chars, allowed extensions: `.md` `.txt` `.json` `.csv` `.py` `.js` `.html`.
   - Cap content at 256 KB.
   - Use existing `object_storage.put_object` (or local fallback if storage not ready).
   - Insert a `user_files` row with `kind="file"`, correct mime_type from extension (text/markdown, text/plain, application/json, etc.).
   - Return `WROTE: name=<filename> id=<file_id> bytes=<n> url=/api/caos/files/<id>/download`.
2. Add `write_file` to the `_TOOL_RX` regex in `aria_tools.py` (lines 320-328).
3. Wire it into `extract_and_run_next_tool_async` (line 416+) — needs `user` + `session_id` from context, which `chat_pipeline.py` line 279-282 currently sets in `_tool_context` (extend with `user_email` and `session_id`).
4. Add documentation to the tools block in `prompt_builder.py` line 117+:
   ```
   [TOOL: write_file name=<filename.md> content=<text>] — saves a file to your CAOS Files. The user will see it in Profile → Files. Use this to deliver formatted reports, trackers, or notes. Filename must include extension; allowed: .md .txt .json .csv .py .js .html. Content cap: 256 KB.
   ```
5. Limit to **3 writes per reply** (matches the existing `tool_iterations < 4` cap).
6. Frontend: zero changes needed — the file appears in `Profile → Files` automatically because the existing `GET /api/caos/files` already lists `user_files` rows.

**Test plan:** curl-prompt Aria with "Save a markdown report titled 'budget.md' with the headings Income, Expenses, Net" and verify (a) the file appears via `GET /api/caos/files?user_email=...` (b) the content is downloadable via `GET /api/caos/files/<id>/download`.

---

## 4. ESTIMATE SUMMARY

| Task | Approved by user? | Credits |
|---|---|---|
| Latency fix (Issue 1) | Pending | ~25 |
| PDF Path B (Issue 2) | **Path B confirmed; Path A rejected** | ~35 |
| write_file tool (Issue 3) | Pending | ~30 |
| Optional: parallelize DB awaits | Pending | +10 |
| **Total (all 3)** | | **~90–100 credits** |

The user has NOT yet said "GO". Wait for explicit approval before writing any code.

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

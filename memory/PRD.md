# CAOS — Emergent Replatform PRD

## Original Problem Statement
Port Base44 CAOS (serverless, Deno + Base44 entities) to a clean full-stack React + FastAPI + MongoDB architecture on Emergent. Preserve all behaviors, governance, and UX clarity from the Base44 live build. Aria = persona, CAOS = platform.

## Authoritative Contracts (binding)
- **System Blueprint v2** — governance invariants (sections 0–20)
- **TSB Log Part 1+2** — TSB-001 through TSB-061
- **File size**: 200 preferred / 400 hard max
- **GOV v1.2 Amendment A**: ≥300-line files get extractions, not inline growth
- **Aria ≠ CAOS**: authority domain separation (Section 0.8)
- **Pull-only awareness**: no polling, no silent writes (Section 0.9)
- **Build → Test → Lock**
- **Edit tracking**: `Changed: <file> +N lines` after every modifying response

## Providers (target state)
| Provider | Key source | Status |
|---|---|---|
| Anthropic Claude (default) | Emergent Universal Key | ✅ Available |
| OpenAI gpt-5.2 | Emergent Universal Key | ✅ Available |
| Google Gemini | Emergent Universal Key | ✅ Available |
| xAI Grok | User's `XAI_API_KEY` (BYO) | Deferred — "2-second fix later" |

TTS: OpenAI tts-1-hd (message bubbles). Google Web Speech (input bar). Locked paths.
STT: OpenAI Whisper / gpt-4o-transcribe.

## Implemented on Emergent (as of Apr 20, 2026)

### Backend — already live
- `/api/caos/sessions` (create/list) + `/api/caos/sessions/{id}/messages|artifacts|continuity`
- `/api/caos/chat` — routed inference with provider/model selection
- `/api/caos/memory/save` + `/memory/{id}` CRUD (structured memory, personal_facts bin, global bin)
- `/api/caos/voice/transcribe` + `/voice/tts` + `/voice/settings`
- `/api/caos/runtime/catalog` + `/runtime/settings`
- `/api/caos/files` upload/link
- `/api/caos/profile/{email}` upsert/get
- Real `tiktoken` WCW metering, retention explanations, rehydration ordering

### Frontend — Base44 parity pass (Apr 20, 2026) ✅
- **ShellHeader**: 3-column — identity chip (L) / `CAOS` + "Cognitive Adaptive Operating System" (C) / thread pill + search + live WCW meter (R)
- **EngineChip**: single pill `⚡ Claude — click to switch` above composer; opens 4-provider menu (Claude/OpenAI/Gemini/Grok-BYO)
- **SelectionReactionPopover**: text-selection-driven popover with 7 emoji reactions + Read/Reply/Copy; positions near selection, dismisses on outside click
- **SearchDrawer**: full rewrite — snippet builder with `<mark>` highlighted match terms, match count + message count
- **Composer**: auto-growing textarea (1–6 rows, then internal scroll), Shift+Enter for newline, Enter sends, removed the weird live-transcript bar
- **MessagePane**: "Receipt" button → "Context"; inline panel heading → "Context Diagnostics"
- **InspectorPanel**: "Why this reply fits" → "Context Diagnostics"
- **CaosShell**: WorkingContextStrip removed from main canvas (moved into header WCW meter); ModelBar row removed; identity chip in header + rail footer duplicate hidden
- **Starfield**: ambient CSS starfield behind the shell, matches Base44 feel
- **CSS file**: `caos-base44-parity.css` (225 lines) — all new overrides isolated for easy rollback

## Governance / File Sizes (current)
| File | Lines | Status |
|---|---|---|
| `useCaosShell.js` | 435 | ⚠️ OVER 400 — flagged for extraction pass (blueprint §2.2) |
| `EngineChip.js` | 73 | ✅ |
| `SelectionReactionPopover.js` | 103 | ✅ |
| `ShellHeader.js` | 96 | ✅ |
| `CaosShell.js` | ~290 | ✅ |
| `Composer.js` | ~145 | ✅ |
| `MessagePane.js` | ~180 | ✅ |
| `SearchDrawer.js` | 99 | ✅ |
| `backend/app/routes/caos.py` | 339 | 🟡 300-line threshold tripped — future-extract gate |
| `backend/app/schemas/caos.py` | 394 | 🟡 near limit |

## P0 Backlog (next tasks)
- [ ] Extract `useCaosShell.js` (435 → split into `useShellBootstrap`, `useShellChat`, `useShellMemory`, `useShellVoice`) — only blueprint breach in app code
- [ ] Rail account menu duplicate — consolidate identity surfaces (cleanup)
- [ ] Wire `SelectionReactionPopover` reply → actually saves as threaded reply on the source message
- [ ] `responseReviewer`-equivalent post-inference policy gate (TSB-053 parity)
- [ ] `mbcrEngine`/TRH v1 parity module behind `chat_pipeline` (TSB-054, TSB-029)

## P1 Backlog
- [ ] Grok provider adapter (~10 LOC, user supplies XAI_API_KEY)
- [ ] MemoryWorkbench refactor (363 lines, near limit)
- [ ] Onboarding tour (Section 20 of blueprint — target Apr 19, 2026)
- [ ] SSE streaming path (TSB-036 parity, kill-switch off by default)

## P2 / Future
- [ ] CTC ARC Inspector panel (browse ContextSeed records)
- [ ] PyAnnote/SpeechBrain audio blueprint (Section 13)
- [ ] Connectors (Google Workspace, GitHub)

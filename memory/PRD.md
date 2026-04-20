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

## Next Action Items
- Phase 4: Orchestrated Swarm v1 — LangGraph Supervisor → Claude Opus JSON planner → E2B Sandbox workers → Critic (E2B key already in `.env`).
- Drive app manually — confirm Synthesizer UI + Show-sources toggle feel right end-to-end.
- Port bubble/* extractions (CopyBlock/LinkPreview/YouTubeEmbed) per TSB-025/027/028.
- Gemini provider adapter with native Google Search grounding (unlocks Google Workspace route).
- responseReviewer post-inference gate (TSB-053).
- mbcrEngine + TRH v1 thread rehydration (TSB-054, TSB-029).
- Resend email integration for selection menu email button.
- Google Workspace (Gmail/Drive/Calendar) via Emergent Google auth.

## Future / Backlog
- RSoD + errorClassifier (TSB-024)
- WCWStatusBadge (color tiers)
- Grok provider adapter (user XAI_API_KEY)
- Onboarding tour (§20)
- CTC ARC Inspector panel
- Emergent platform: TTS `/llm/audio/speech` 500 ticket (draft delivered; browser speechSynthesis fallback unblocks users)

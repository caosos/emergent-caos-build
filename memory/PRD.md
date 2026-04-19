# CAOS Replatform PRD

## Original Problem Statement
Replatform CAOS away from the Base44/Deno serverless environment into a normal full-stack architecture with a Python FastAPI backend and React/Next-style frontend. The active goals are preserving CAOS continuity/memory, replacing monoliths with modular services, and moving the shell closer to the real CAOS layout: persistent app sidebar, open canvas, high-fidelity menus, files/photos/links, richer bubble controls, artifacts, lineage, and voice/file behaviors on top of the Python backend.

## Architecture Decisions
- Backend runtime: FastAPI (Python) with MongoDB in this workspace.
- Canonical isolation boundary: `session_id`.
- Canonical context pipeline: ingest -> sanitize -> compress -> retrieve -> inject -> receipt.
- Working Context Window (WCW) is a contract surface and must ultimately be derived from actual token usage inside the active session so hydration/sanitization effectiveness can be measured honestly.
- Artifact model now includes receipts, thread summaries, context seeds, user files/links, and lineage fields across receipts/summaries/seeds.
- LLM runtime for chat and voice: OpenAI services via the Emergent universal key (`gpt-5.2`, `tts-1-hd`, `whisper-1`).
- Frontend migration path: CAOS shell with persistent app-style sidebar, open center canvas, live chat pane, composer, thread search drawer, WCW meter, receipt/continuity cards, profile drawer, files/artifacts drawer, and richer bubble controls.

## What's Implemented
- Modular backend foundation under `backend/app/` with config, DB access, schemas, context engine, prompt builder, artifact builder, file storage service, voice service, chat pipeline, and CAOS routes.
- Session-scoped endpoints: contract, profile upsert/get, session creation/listing, message storage, structured memory save, context preparation, session artifacts, session continuity, real chat turns, file upload/list/link/download, backend TTS, and backend STT.
- Artifact persistence on each chat turn: receipts, thread summaries, and context seeds with lineage fields (`previous_*`, `source_message_ids`, `lineage_depth`) for continuity and future rehydration.
- Real CAOS shell frontend with persistent sidebar navigation, recent threads list, centered open canvas, live message pane, composer, floating search drawer, WCW meter, receipt card, continuity card, profile drawer, files/artifacts drawer, and bootstrap cleanup for fresh identities.
- Richer CAOS surfaces ported into the shell: working header menu, file upload + saved links, copy action for all messages, backend read-aloud action for assistant messages, microphone transcription flow, graceful action feedback/errors, inline replies, Useful reaction chips, and inline linked receipt panels.
- Backend regression tests and browser validation for shell/chat/artifact/file/voice/menu/continuity flows.
- Added a dedicated System Blueprint and TSB log in `/app/memory` so architecture and recurring failures are documented for the team.
- Simplified the shell hierarchy based on latest feedback: left rail owns new-thread/navigation behavior, header is lighter, search is icon-first, and user identity is moving into the lower rail instead of living in the header.
- Continued the shell cleanup: user identity now sits in the lower rail with settings/files/logout, and the top search surface has been reduced toward a compact inspector-style interaction.
- Began the command-center parity shift: rail search, a calmer empty-state prompt, quick action pills, bottom model bar, and an on-demand inspector instead of a permanently heavy right column.
- Locked the next shell move: sticky left rail, full-width fixed bottom command footer, and input-bar read-aloud for the last assistant message alongside per-bubble TTS.
- Removed the Emergent badge markup from `frontend/public/index.html` and verified in preview that the badge text is gone.
- Added a portable runtime layer for CAOS so model/provider routing now resolves from stored user runtime preferences instead of being hard-wired to one inference engine.
- Added runtime settings endpoints and catalog support for OpenAI/Claude/Gemini via the Emergent Universal Key, with Grok/xAI staged honestly as a BYO-provider placeholder until credentials are attached.
- Deepened the memory pipeline with subject-bin inference, continuity packet selection from prior summaries/seeds, and deterministic reinjection metadata returned in chat receipts.
- Finished the shell’s viewport-lock pass: the app now runs as a viewport-contained workspace with a collapsible left rail, a bottom-spanning command footer, and refreshed model routing controls in the shell UI.
- Added runtime visibility to the profile drawer and exposed provider chips in the model bar so the user can switch between supported engines from the CAOS shell.
- Added the Phase 1 voice/settings pass: profile-based voice preferences, GPT-4o Transcribe as the preferred STT target, whisper-1 fallback handling, selectable TTS voices, and composer draft-preservation during mic capture.
- Added a streaming-style transcription UX in the composer: chunk-based interim transcript updates are shown live while recording, then replaced with the finalized transcript on stop so typed draft text is preserved.
- Added Phase 2A lane-aware memory: sessions now persist a derived lane, receipts carry lane/worker/context-budget metadata, cross-thread continuity now ranks prior summaries/seeds across the user’s sessions, and lane worker snapshots are rebuilt into `/api/caos/memory/workers/*` endpoints.
- Added visible lane surfaces in the shell so thread cards and the inspector expose lane + worker usage instead of hiding continuity decisions.
- Started the canonical shell/menu rewrite: the sidebar remains collapsible and visible by default, while a new rail account menu now holds the user identity, grouped actions, side-panel options, and session token access instead of relying on competing menu patterns.
- Simplified the top bar into a cleaner CAOS header so the identity model is anchored in the sidebar and the chat surface can move closer to screenshot parity.
- Continued the `/chat` visual parity pass: added a compact in-surface chat strip for working packet/lane/continuity/actions, tightened message cards, moved search/context/files actions into the chat surface, and reshaped the composer into a slimmer bright control surface while keeping all existing functionality intact.
- Added overlay-style previous threads behavior with multiple entry points (chat strip, header thread pill, sidebar Threads button), giving the workspace a dedicated thread-switching surface closer to the screenshot contract.
- Refined chat workspace hierarchy further: grouped quick actions + model routing into a dedicated command dock above the composer and constrained overlay panels so Previous Threads / Search / Context read as workspace layers rather than colliding with the bottom operating controls.
- Tightened the message stream itself: denser bubbles, shorter timestamps, slimmer action rows, and clearer bubble separation between user/assistant messages so `/chat` reads more like the intended CAOS command surface.
- Tightened the right-side panels as part of `/chat` parity: Search now shows active thread scope + visible hit count, and Inspector now opens with a compact receipt grid and packet summary so those surfaces behave like compact operational panels rather than generic drawers.
- Tightened the center workspace header/strip proportions: active-thread title/session info and top chat strip now render as a denser control band, reducing top-of-pane sprawl and moving the workspace closer to the screenshot contract.
- Tightened message-lane alignment: user bubbles now anchor to the right and assistant/system bubbles anchor to the left inside the center stream, making the chat body behave more like a true conversation lane and less like stacked full-width cards.
- Tightened left-rail and center-canvas proportions together: reduced sidebar width, tightened rail controls, narrowed the message canvas and bubble widths, and improved the overall shell silhouette so `/chat` reads closer to the CAOS reference.
- Removed the in-pane working packet / lane / continuity strip from the main viewing area so the conversation lane stays cleaner. Search/Threads remain accessible via header/rail, and Inspector access now lives behind the left-rail Tools entry instead of occupying the center workspace.
- Added calmer workspace-state behavior: left-rail nav now reflects the active surface, the header route label updates dynamically, and the command toolbar collapses away while side panels like Threads/Tools/Search/Projects are open so the main input remains the only persistent bottom control.

## Prioritized Backlog
### P0
- Deepen the artifact contracts further so receipts, summaries, seeds, and subject bins can support longer-horizon rehydration across multiple threads and lanes with stronger lane heuristics and worker summarization.
- Build the actual BYO-provider credential attachment flow for non-Universal engines like Grok/xAI instead of the current placeholder-only registration.
- Port the remaining repo bubble/menu surfaces still missing: richer receipt detail, metadata rows, expanded reply/reaction parity, and deeper command-center home states.
- Build stronger observability/error-envelope handling and reduce any remaining startup noise.
- Validate whether `gpt-4o-transcribe` can be made fully primary in the current STT integration path; today the system attempts it first and falls back honestly to `whisper-1` when required.

### P1
- Build richer thread rehydration workers, memory summaries, and controlled cross-thread retrieval policy on top of the new lane-aware lineage model.
- Add better retrieval ranking, metadata tagging, bin governance, and thread title generation.
- Bring over full files/photos/links parity and richer message evidence surfaces from the repo.
- Deepen the voice surface further with true streaming transcription transport, richer recording state controls, and transcript receipts tied to artifacts.

### P2
- Connector framework for Gmail/Workspace/home automation actions.
- Account-level storage isolation strategy and migration tooling.
- Deeper anchor maps, campaign memory, and long-horizon project continuity.

## Next Tasks
1. Continue the `/chat` visual parity pass: keep tightening message density, drawer sizing, and surface hierarchy toward the screenshot contract.
2. Deepen receipts/summaries/seeds again so subject bins, continuity packets, and cross-thread rehydration become first-class long-horizon memory primitives with stricter cost budgets.
3. Build the secure BYO-provider credential attachment flow so Grok/xAI and future non-Universal engines can be plugged into CAOS without changing the memory architecture.

## Living Contract Tracking
- Master implementation checklist: `/app/memory/MASTER_IMPLEMENTATION_CHECKLIST.md`

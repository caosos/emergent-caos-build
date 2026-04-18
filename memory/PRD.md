# CAOS Replatform PRD

## Original Problem Statement
Replatform CAOS away from the Base44/Deno serverless environment into a normal full-stack architecture with a Python FastAPI backend and React/Next-style frontend. The active goals are preserving CAOS continuity/memory, replacing monoliths with modular services, and moving the shell closer to the real CAOS layout: persistent app sidebar, open canvas, high-fidelity menus, files/photos/links, richer bubble controls, artifacts, lineage, and voice/file behaviors on top of the Python backend.

## Architecture Decisions
- Backend runtime: FastAPI (Python) with MongoDB in this workspace.
- Canonical isolation boundary: `session_id`.
- Canonical context pipeline: ingest -> sanitize -> compress -> retrieve -> inject -> receipt.
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

## Prioritized Backlog
### P0
- Deepen the artifact contracts so receipts, summaries, and seeds more faithfully support thread rehydration and campaign continuity.
- Port the remaining repo bubble/menu surfaces still missing: richer receipt detail, metadata rows, expanded reply/reaction parity, and deeper command-center home states.
- Build stronger observability/error-envelope handling and reduce any remaining startup noise.
- Improve user identity handling so the shell can support real auth later without rewiring the chat core.

### P1
- Port the original TTS/STT settings surfaces and voice preference controls.
- Build thread rehydration workers, memory summaries, and controlled cross-thread retrieval policy on top of the new lineage model.
- Add better retrieval ranking, metadata tagging, and thread title generation.
- Bring over full files/photos/links parity and richer message evidence surfaces from the repo.

### P2
- Connector framework for Gmail/Workspace/home automation actions.
- Account-level storage isolation strategy and migration tooling.
- Deeper anchor maps, campaign memory, and long-horizon project continuity.

## Next Tasks
1. Push the shell from improved parity to true parity: deeper home-state command center, richer metadata rows, and better spacing/negative space matching the original CAOS screenshots.
2. Deepen receipts/summaries/seeds so they carry stronger rehydration lineage and richer evidence detail.
3. Rebuild full voice settings, files/photos/links parity, and then prepare the shell for real auth and connector work.

# CAOS Replatform PRD

## Original Problem Statement
Replatform CAOS away from the Base44/Deno serverless environment into a normal full-stack architecture with a Python FastAPI backend and React/Next-style frontend. The active goals are preserving CAOS continuity/memory, replacing monoliths with modular services, and porting the richer shell surfaces: header menus, files/photos/links, richer bubble controls, artifacts, and voice/file behaviors on top of the Python backend.

## Architecture Decisions
- Backend runtime: FastAPI (Python) with MongoDB in this workspace.
- Canonical isolation boundary: `session_id`.
- Canonical context pipeline: ingest -> sanitize -> compress -> retrieve -> inject -> receipt.
- Artifact model now includes receipts, thread summaries, context seeds, and user files/links.
- LLM runtime for chat and voice: OpenAI services via the Emergent universal key (`gpt-5.2`, `tts-1-hd`, `whisper-1`).
- Frontend migration path: CAOS shell with thread rail, live chat pane, composer, thread search, WCW meter, right-side receipt/memory column, profile drawer, files/artifacts drawer, and richer bubble controls.

## What's Implemented
- Modular backend foundation under `backend/app/` with config, DB access, schemas, context engine, prompt builder, artifact builder, file storage service, voice service, chat pipeline, and CAOS routes.
- Session-scoped endpoints: contract, profile upsert/get, session creation/listing, message storage, structured memory save, context preparation, session artifacts, real chat turns, file upload/list/link/download, backend TTS, and backend STT.
- Artifact persistence on each chat turn: receipts, thread summaries, and context seeds.
- Real CAOS shell frontend with previous-thread rail, live message pane, composer, thread search, WCW meter, right-side receipt/memory column, and saved receipt hydration after reload.
- Richer CAOS surfaces ported into the shell: header menu, profile drawer, Files & Artifacts drawer, file upload + saved links, copy action for all messages, backend read-aloud action for assistant messages, and graceful action feedback/errors.
- Composer now supports backend file upload and microphone capture feeding backend transcription.
- Backend regression tests and browser validation for shell/chat/artifact/file/voice flows.

## Prioritized Backlog
### P0
- Port the remaining high-fidelity CAOS shell behaviors from the repo: deeper header/menu flows, files/photos/links parity, and richer bubble controls/replies/receipts.
- Expand artifact contracts further so receipts, summaries, and seeds better match the original CAOS truth surface and lineage.
- Build stronger observability/error-envelope handling instead of raw exception text and reduce first-time profile bootstrap noise.
- Improve user identity handling so the shell can support real auth later without rewiring the chat core.

### P1
- Port the original TTS/STT settings surfaces and voice preference controls.
- Build thread rehydration, memory summaries, and controlled cross-thread retrieval policy.
- Add receipt/evidence expansion inside message bubbles.
- Add better retrieval ranking, metadata tagging, and thread title generation.

### P2
- Connector framework for Gmail/Workspace/home automation actions.
- Account-level storage isolation strategy and migration tooling.
- Deeper anchor maps, campaign memory, and long-horizon project continuity.

## Next Tasks
1. Port the remaining bubble-level controls and richer receipt/evidence surfaces from the repo.
2. Deepen receipts/summaries/seeds so they support thread rehydration and long-horizon continuity more faithfully.
3. Rebuild full voice settings, files/photos/links parity, and then prepare the shell for real auth and connector work.

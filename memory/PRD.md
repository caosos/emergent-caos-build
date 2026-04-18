# CAOS Replatform PRD

## Original Problem Statement
Replatform CAOS away from the Base44/Deno serverless environment into a normal full-stack architecture with a Python FastAPI backend and React/Next-style frontend. The first logical moves are the memory-centered backend and then the real CAOS shell: session isolation, sanitization, relevance-only reinjection, searchable/indexable metadata-aware retrieval, receipts, summaries, seeds, and richer shell surfaces without monolith files.

## Architecture Decisions
- Backend runtime: FastAPI (Python) with MongoDB in this workspace.
- Canonical isolation boundary: `session_id`.
- Canonical context pipeline: ingest -> sanitize -> compress -> retrieve -> inject -> receipt.
- Replatform strategy: preserve CAOS product behavior and shell layout while replacing Base44 auth/entities/functions with modular Python services.
- LLM runtime for the chat pipeline: OpenAI `gpt-5.2` through the Emergent universal key.
- Frontend migration path: move from the temporary workbench into a CAOS shell with thread rail, chat pane, composer, receipt/context column, profile drawer, artifacts drawer, and richer message actions.

## What's Implemented
- Modular backend foundation under `backend/app/` with config, DB access, schemas, context engine, prompt builder, artifact builder, chat pipeline, and CAOS routes.
- Session-scoped endpoints: contract, profile upsert/get, session creation/listing, message storage, structured memory save, context preparation, session artifacts, and real chat turns.
- Real Python chat orchestration endpoint (`POST /api/caos/chat`) that stores the user turn, sanitizes the session, retrieves structured memory, builds the system prompt, calls the LLM, stores the assistant reply, and returns receipt + WCW metadata.
- Artifact persistence on each chat turn: receipts, thread summaries, and context seeds.
- Real CAOS shell frontend replacing the workbench: header, previous-thread rail, live message pane, composer, thread search filter, WCW meter, and right-side receipt/memory column.
- Richer CAOS surfaces ported into the shell: profile drawer, Files & Artifacts drawer, copy action for all messages, browser read-aloud action for assistant messages, and graceful action feedback/errors.
- Receipt column now hydrates from saved artifacts after reload.
- Backend regression tests and frontend/browser validation for the upgraded shell + artifact flow.

## Prioritized Backlog
### P0
- Expand the data model further to cover files, links, photos, richer receipts, cross-thread summaries, and seed lineage from the original CAOS system.
- Port the higher-fidelity CAOS shell surfaces still missing from the Base44 version: header menus, profile toggles, files/photos/links management, and richer bubble controls.
- Build stronger observability/error-envelope handling instead of raw exception text.
- Improve user identity handling so the shell can support real auth later without rewiring the chat core.

### P1
- Port TTS/STT contracts into Python services and reconnect them to the shell.
- Build thread rehydration, memory summaries, and controlled cross-thread retrieval policy.
- Add receipt/evidence expansion inside message bubbles.
- Add better retrieval ranking, metadata tagging, and thread title generation.

### P2
- Connector framework for Gmail/Workspace/home automation actions.
- Account-level storage isolation strategy and migration tooling.
- Deeper anchor maps, campaign memory, and long-horizon project continuity.

## Next Tasks
1. Port the remaining high-value CAOS surfaces from the repo: header menu flows, file/media management, and richer message controls.
2. Deepen the Python data model and artifact contracts so receipts/summaries/seeds become closer to the original CAOS truth surface.
3. Rebuild voice, file, and profile behaviors on top of the new backend contract and prepare for real auth.

# CAOS Replatform PRD

## Original Problem Statement
Replatform CAOS away from the Base44/Deno serverless environment into a normal full-stack architecture with a Python FastAPI backend and React/Next-style frontend. The first logical move is the memory-centered backend: session isolation, sanitization, relevance-only reinjection, searchable/indexable metadata-aware retrieval, and modular files under the monolith threshold. The next move is replacing the temporary workbench with the real CAOS shell and wiring a real Python chat/orchestration pipeline underneath it.

## Architecture Decisions
- Backend runtime: FastAPI (Python) with MongoDB in this workspace.
- Canonical isolation boundary: `session_id`.
- Canonical context pipeline: ingest -> sanitize -> compress -> retrieve -> inject -> receipt.
- Replatform strategy: preserve CAOS product behavior and shell layout while replacing Base44 auth/entities/functions with modular Python services.
- LLM runtime for the new chat pipeline: OpenAI `gpt-5.2` through the Emergent universal key.
- Frontend migration path: move from the temporary Memory Workbench into a CAOS shell with thread rail, chat pane, receipt/context column, and real composer.

## What's Implemented
- Modular backend foundation under `backend/app/` with config, DB access, schemas, context engine, prompt builder, chat pipeline, and CAOS routes.
- Session-scoped endpoints: contract, profile upsert, session creation/listing, message storage, structured memory save, context preparation, and real chat turns.
- Deterministic context engine for low-signal cleanup, duplicate removal, compression, memory ranking, and receipt generation.
- Real CAOS shell frontend replacing the temporary workbench: header, previous-thread rail, live message pane, composer, thread search filter, WCW meter, and right-side receipt/memory column.
- Python chat orchestration endpoint (`POST /api/caos/chat`) that stores the user turn, sanitizes the session, retrieves structured memory, builds the system prompt, calls the LLM, stores the assistant reply, and returns receipt + WCW metadata.
- Visible shell error handling for failed actions.
- Backend regression tests and frontend/browser validation for the current shell + pipeline flow.

## Prioritized Backlog
### P0
- Expand the data model to cover files, receipts, summaries, seeds, and thread state from the original CAOS system.
- Port the current Base44 shell surfaces with higher fidelity: header menu, profile drawer, files/photos/links surfaces, richer bubble actions, and thread search parity.
- Build stronger observability/error-envelope handling instead of raw exception text.
- Improve session bootstrap and user identity handling so the shell can support real auth later without rewiring the chat core.

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
1. Port the higher-fidelity CAOS shell surfaces from the Base44 repo into this frontend without reintroducing monolith files.
2. Expand the Python data model and receipts so the chat pipeline can carry more of the original CAOS truth surface.
3. Rebuild voice, files, and profile surfaces on top of the new backend contract.

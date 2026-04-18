# CAOS Replatform PRD

## Original Problem Statement
Replatform CAOS away from the Base44/Deno serverless environment into a normal full-stack architecture with a Python FastAPI backend and React/Next-style frontend. The first logical move is the memory-centered backend: session isolation, sanitization, relevance-only reinjection, searchable/indexable metadata-aware retrieval, and modular files under the monolith threshold.

## Architecture Decisions
- Backend runtime: FastAPI (Python) with MongoDB in this workspace.
- Canonical isolation boundary: `session_id`.
- Canonical context pipeline: ingest -> sanitize -> compress -> retrieve -> inject -> receipt.
- Replatform strategy: preserve CAOS product behavior and memory model while replacing Base44 auth/entities/functions with modular Python services.
- Frontend milestone for this phase: a visible Memory Workbench to exercise the backend contract before rebuilding the full CAOS shell.

## What's Implemented
- Modular backend foundation under `backend/app/` with config, DB access, schemas, context engine, and CAOS routes.
- Session-scoped endpoints: contract, profile upsert, session creation, message storage, structured memory save, and context preparation.
- Deterministic context engine for low-signal cleanup, duplicate removal, compression, memory ranking, and receipt generation.
- Frontend CAOS Memory Workbench for creating a session, saving memory, adding messages, preparing context, and inspecting receipts.
- Explicit error handling UI for each workbench action.
- Regression test coverage for the new CAOS API endpoints.

## Prioritized Backlog
### P0
- Build the real CAOS chat orchestration API around this memory contract.
- Replace temporary workbench-only flows with authenticated user/session handling.
- Expand data model to cover conversations, files, receipts, summaries, and connector events.
- Add durable indexing/search strategy for names, tags, timestamps, and semantic retrieval.

### P1
- Port TTS/STT contracts into Python services.
- Build thread rehydration, memory summaries, and cross-thread retrieval policy.
- Create a proper CAOS app shell frontend instead of the workbench.
- Add inline observability surfaces for receipts and context decisions.

### P2
- Connector framework for Gmail/Workspace/home automation actions.
- Account-level storage isolation strategy and migration tooling.
- Deeper ranking logic, anchor maps, and long-horizon project memory.

## Next Tasks
1. Design the canonical CAOS data model beyond profile/messages: files, receipts, summaries, seeds, and thread state.
2. Build the Python chat pipeline service that consumes the session-scoped context-prep output.
3. Start replacing the workbench with the first real CAOS shell and message flow.

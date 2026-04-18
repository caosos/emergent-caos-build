# CAOS Replatform Notes

## Locked first invariant
- Session isolation is the primary memory boundary.
- `session_id` is the canonical identifier for message history, sanitization, retrieval, and reinjection.
- No cross-session retrieval is allowed unless an explicit future cross-thread policy says otherwise.

## Current backend foundation
- FastAPI + Python runtime
- MongoDB persistence in this workspace
- Modular context engine split away from the request router
- Deterministic context prep endpoint for sanitize/compress/retrieve flow

## First working backend endpoints
- `GET /api/caos/contract`
- `POST /api/caos/sessions`
- `POST /api/caos/messages`
- `GET /api/caos/sessions/{session_id}/messages`
- `POST /api/caos/profile/upsert`
- `POST /api/caos/memory/save`
- `POST /api/caos/context/prepare`

## Why this is first
The product lives or dies on isolation, retrieval, sanitization, and relevance injection. UI comes after the memory contract is stable.
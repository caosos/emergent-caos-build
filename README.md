# CAOS — Emergent Build

CAOS (Cognitive Adaptive Operating System) is a personal AI platform focused on persistent memory, tool orchestration, multi-provider inference, diagnostics, receipts, and admin-governed system evolution.

This repository is the Emergent-hosted CAOS application codebase. It contains the backend services, frontend UI, memory/receipt systems, connector integrations, and diagnostic/admin surfaces used by Aria.

## AI / Agent Start Here

If you are ChatGPT, Claude, Gemini, Emergent Agent, GitHub Copilot, or another code-reading agent, start with these files before making claims about the repo:

1. `AGENTS.md` — mandatory inspection and safety protocol for AI agents.
2. `docs/REPO_MAP.md` — searchable module map and file ownership guide.
3. `docs/LATENCY_AND_TURNTRACE.md` — latency, hydration, proactivity, and TurnTrace architecture.
4. `backend/app/services/chat_pipeline.py` — primary chat orchestration spine.
5. `backend/app/services/hydration_policy.py` — context hydration decision logic.
6. `backend/app/services/proactivity_policy.py` — proactive department wake policy.
7. `backend/app/services/surface_registry.py` — UI/capability surface registry.
8. `backend/app/services/turn_trace.py` — per-turn forensic latency ledger.
9. `backend/app/services/artifact_builder.py` — persisted receipts, summaries, and seeds.
10. `frontend/src` — React frontend application surface.

## Repository Layout

```text
backend/       Python backend, API routes, services, models, diagnostics, connectors
frontend/      React frontend application and UI surfaces
memory/        Memory-related artifacts / supporting material
tests/         Test files and smoke checks
test_reports/  Generated or saved test reports
docs/          Human/AI-readable architecture and repo maps
```

## Current Architectural Spine

The current runtime spine is centered on:

```text
backend/app/services/chat_pipeline.py
```

That file coordinates:

- session/profile setup
- quota check
- history fetch and compression
- memory ranking
- hydration policy
- proactivity policy
- connector/tool availability
- prompt build
- LLM execution
- tool/MCP loop
- receipts
- summaries/seeds
- background aftermath

The goal is to preserve behavior while gradually extracting large responsibilities into smaller modules.

## Latency / Context Direction

The latency strategy is not to remove capability. The strategy is:

```text
right context
right time
right reason
measured cost
receipt-backed diagnosis
```

Important concepts:

- Hydration gates keep departments/tools on standby until relevant.
- Proactivity policy decides what should wake up based on user intent.
- TurnTrace records what actually cost time during a turn.
- Admin users may inspect internal diagnostics.
- Normal users receive plain-language explanations and support-ticket paths, not raw internal code/receipt details.

## Branch / Tooling Note

Some AI/GitHub tools have trouble browsing branch names containing `/`. Prefer slash-free branch names for agent-created branches when possible, for example:

```text
fix-turntrace-ledger-v1
docs-repo-discovery-v1
refactor-chat-tool-loop-v1
```

Existing slash branches are valid Git branches, but slash-free names are more reliable across lightweight web-fetch and connector tools.

## Non-Negotiable Preserve List

Do not remove or silently degrade:

- tools
- connectors
- memory
- summaries
- seeds
- receipts
- lane workers
- file handling
- diagnostic tools
- support tickets
- proactive capability
- admin diagnostics

Optimization must be done by gating, measuring, extracting, caching, or isolating — not by deleting capability.

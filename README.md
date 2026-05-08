# CAOS — Working Prototype

**CAOS** — Cognitive Adaptive Operating System — is a governed AI platform prototype focused on persistent memory, tool orchestration, multi-provider inference, diagnostics, receipts, context hydration, and admin-governed system evolution.

This repository contains the fuller working prototype codebase from the Emergent-hosted CAOS build. It includes backend services, frontend UI, memory/receipt systems, connector integrations, diagnostic/admin surfaces, and the Aria-oriented chat/runtime experience.

If you want to inspect the actual prototype code, start here.

If you want the clean server-target rebuild and public roadmap, see:

- [`caosos/linode-repo`](https://github.com/caosos/linode-repo)

Private CAOSCare implementation code is not published here.

## What CAOS Explores

CAOS is built around the idea that AI systems should not only answer prompts. They should operate inside a governed workbench with:

- persistent memory;
- context hydration and ranking;
- tool and connector access;
- receipts and diagnostics;
- multi-provider inference direction;
- admin-visible system state;
- support-ticket and troubleshooting surfaces;
- governed evolution instead of silent mutation.

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

- session/profile setup;
- quota check;
- history fetch and compression;
- memory ranking;
- hydration policy;
- proactivity policy;
- connector/tool availability;
- prompt build;
- LLM execution;
- tool/MCP loop;
- receipts;
- summaries/seeds;
- background aftermath.

The goal is to preserve useful behavior while gradually extracting large responsibilities into smaller modules.

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

## Public / Private Boundary

Public here:

- CAOS prototype code;
- architecture docs;
- memory/tool/orchestration experiments;
- frontend/backend prototype surfaces;
- diagnostics and receipts concepts;
- public feedback and forks.

Private elsewhere:

- CAOSCare implementation code;
- facility-specific workflows;
- resident/staff data;
- private deployment credentials;
- sensitive operational screenshots/logs.

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

- tools;
- connectors;
- memory;
- summaries;
- seeds;
- receipts;
- lane workers;
- file handling;
- diagnostic tools;
- support tickets;
- proactive capability;
- admin diagnostics.

Optimization must be done by gating, measuring, extracting, caching, or isolating — not by deleting capability.

## License

This repository is released under the MIT License. See [`LICENSE`](LICENSE).

## Feedback

Feedback is welcome, especially on:

- memory architecture;
- context hydration;
- tool/MCP loop safety;
- model routing;
- worker-agent orchestration;
- receipt-backed diagnostics;
- frontend/admin UX;
- clean rebuild strategy.

For the clean rebuild roadmap, see [`caosos/linode-repo`](https://github.com/caosos/linode-repo).

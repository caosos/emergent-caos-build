# CAOS — Working Prototype

**CAOS** — Cognitive Adaptive Operating System — is a governed AI platform prototype focused on persistent memory, tool orchestration, multi-provider inference, diagnostics, receipts, context hydration, and admin-governed system evolution.

This repository contains the fuller working prototype codebase from the Emergent-hosted CAOS build. It includes backend services, frontend UI, memory/receipt systems, connector integrations, diagnostic/admin surfaces, and the Aria-oriented chat/runtime experience.

If you want to inspect the actual prototype code, start here.

If you want the clean server-target rebuild and public roadmap, see:

- [`caosos/linode-repo`](https://github.com/caosos/linode-repo)

Private CAOSCare implementation code is not published here.

## Built For User-Owned AI

CAOS is built for privacy, personalization, and user-directed AI experience.

The goal is not a generic chatbot that forgets who you are every session. The goal is an AI workbench that can get to know the user, adapt to the user, and remain governed by the user.

Core product principles:

- **Your memory is yours.** CAOS memory is designed around user-owned context, not hidden data harvesting.
- **Your AI should know you because you allow it to.** Personalization should be explicit, inspectable, correctable, and removable.
- **Your experience should be customized to you and by you.** The user should control preferences, memory, models, tools, voice, workflows, and boundaries.
- **Use the model that fits the job.** CAOS is designed for multi-provider inference and future model routing instead of locking every task to one model.
- **Context should be governed.** Relevant context should be hydrated when useful, sanitized when needed, and backed by receipts.
- **Tools need rules.** File, repo, connector, MCP, and agent actions should be permissioned, visible, and auditable.
- **Important answers need checks.** CAOS Council Engine (CCE) is the proposed trust engine for verifier passes, council mode, risk gates, source posture, and receipt-backed synthesis.

In short:

```text
Your memory.
Your models.
Your tools.
Your rules.
```

## What CAOS Explores

CAOS is built around the idea that AI systems should not only answer prompts. They should operate inside a governed workbench with:

- persistent memory;
- user-owned personalization;
- context hydration and ranking;
- tool and connector access;
- receipts and diagnostics;
- multi-provider inference direction;
- CCE / CAOS Council Engine direction for model checking, verifier passes, source review, and council-mode synthesis;
- admin-visible system state;
- support-ticket and troubleshooting surfaces;
- governed evolution instead of silent mutation.

## CCE / CAOS Council Engine Direction

CCE is the proposed core trust engine for CAOS.

It is not a separate chatbot and not a vendor-specific model wrapper. It is the governed orchestration layer for deciding when a response should use one model, one model plus a verifier, a multi-model council, or human-only escalation.

Start here for the proposal:

- [`docs/CCE_CAOS_CARE_ENGINE_PROPOSAL.md`](docs/CCE_CAOS_CARE_ENGINE_PROPOSAL.md)

The immediate product decision is that CAOS Care should use CCE-lite first: intent classification, risk gating, verification, receipts, and human escalation. Full council mode remains appropriate for admin, incident review, policy, research, architecture, and other high-impact workflows.

## AI / Agent Start Here

If you are ChatGPT, Claude, Gemini, Emergent Agent, GitHub Copilot, or another code-reading agent, start with these files before making claims about the repo:

1. `AGENTS.md` — mandatory inspection and safety protocol for AI agents.
2. `docs/REPO_MAP.md` — searchable module map and file ownership guide.
3. `docs/CCE_CAOS_CARE_ENGINE_PROPOSAL.md` — CCE trust-engine proposal and CAOS Care integration direction.
4. `docs/LATENCY_AND_TURNTRACE.md` — latency, hydration, proactivity, and TurnTrace architecture.
5. `backend/app/services/chat_pipeline.py` — primary chat orchestration spine.
6. `backend/app/services/hydration_policy.py` — context hydration decision logic.
7. `backend/app/services/proactivity_policy.py` — proactive department wake policy.
8. `backend/app/services/surface_registry.py` — UI/capability surface registry.
9. `backend/app/services/turn_trace.py` — per-turn forensic latency ledger.
10. `backend/app/services/artifact_builder.py` — persisted receipts, summaries, and seeds.
11. `frontend/src` — React frontend application surface.

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
- CCE / trust-engine proposal;
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

- user-owned memory and personalization;
- memory architecture;
- context hydration;
- tool/MCP loop safety;
- model routing;
- worker-agent orchestration;
- CCE / council-mode trust architecture;
- receipt-backed diagnostics;
- frontend/admin UX;
- clean rebuild strategy.

For the clean rebuild roadmap, see [`caosos/linode-repo`](https://github.com/caosos/linode-repo).

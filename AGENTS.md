# AGENTS.md — CAOS Repo Agent Protocol

This file is the mandatory entry point for AI agents inspecting or modifying this repository.

## Operating Mode

Default mode is inspect-first.

Do not write code until you understand:

1. Which branch/ref is being inspected.
2. Which files are relevant.
3. Whether the task is documentation, frontend, backend, latency, connectors, memory, or deployment.
4. Which capabilities must be preserved.

## Branch Discipline

No agent writes directly to `main`.

Every agent must work from its own slash-free branch with clear ownership or lane attribution.

Required before writing:

1. State the active branch.
2. Confirm the branch exists.
3. State the exact intended files.
4. Write only to that branch.
5. Report the commit SHA after each bounded change.
6. Compare the branch against `main` after writes.
7. Do not merge or deploy production without Michael approval.

Recommended branch style:

```text
aria-ai-hardware-integration
fix-normal-user-aria-continuity-v1
fix-latency-popover-v1
repo-topology-housecleaning-v1
```

Avoid creating new branches with `/` in the name unless Michael explicitly instructs it. Some lightweight GitHub/AI tools handle slash branches poorly.

For stacked work, compare both:

```text
active branch vs main
active branch vs immediate parent branch
```

Direct comparison to `main` can include prior stacked work and overstate the actual change set.

## Mandatory Preserve List

Never remove or silently degrade these systems unless the repository owner explicitly asks for that exact removal:

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

Latency optimization must be achieved by gating, measuring, extracting, caching, or isolating — not by deleting capability.

## Protected Lanes

Do not touch these areas unless explicitly assigned:

```text
backend/app/services/chat_pipeline.py
backend/app/services/hydration_policy.py
backend/app/services/proactivity_policy.py
backend/app/services/surface_registry.py
backend/app/services/turn_trace.py
backend/app/services/artifact_builder.py
receipt schema / latency receipt fields
permanent memory promotion paths
structured_memory / memory atom promotion
admin-vs-user security boundaries
```

If overlap is unavoidable, stop and ask Michael before writing.

## First Files To Read

Before making architectural claims, inspect:

```text
README.md
AGENTS.md
docs/REPO_MAP.md
docs/LATENCY_AND_TURNTRACE.md
docs/agent-field-notes.md
backend/app/services/chat_pipeline.py
backend/app/services/hydration_policy.py
backend/app/services/proactivity_policy.py
backend/app/services/surface_registry.py
backend/app/services/turn_trace.py
backend/app/services/artifact_builder.py
```

If the task is frontend/UI, also inspect likely files under:

```text
frontend/src
```

If the exact component is unknown, search for visible UI text such as:

```text
Response latency
latency_ms
receipt
Admin Dashboard
Memory Console
Support Tickets
```

## Tooling Caveat

GitHub connector search and directory browsing may return false negatives or incomplete results. A failed search is not proof that a file, symbol, route, or component does not exist.

Use the field notes here before relying on connector behavior:

```text
docs/agent-field-notes.md
```

Fallback inspection path:

```text
README.md
AGENTS.md
docs/REPO_MAP.md
docs/LATENCY_AND_TURNTRACE.md
known direct file paths
runtime screenshots / request evidence as clues, then source verification
```

## Change Discipline

Use small, bounded changes.

For runtime changes:

1. Read current file.
2. State intended change.
3. Preserve behavior unless the task explicitly requests behavior change.
4. Keep receipts/tooling/admin paths intact.
5. Prefer extraction over inline growth.
6. Avoid unrelated refactors.

For documentation changes:

1. Do not modify runtime code.
2. Improve repo discoverability.
3. Add search terms agents will actually query.
4. Keep maps current when adding new modules.
5. Prefer updating the top-level README / AGENTS / docs map before creating scattered docs.

## Admin Boundary Rule

Internal system/code reasoning is admin-only.

Admin users may receive:

- TurnTrace internals
- raw latency receipt explanations
- repo/code path analysis
- PR diagnostics
- connector/tool timing analysis
- system architecture reasoning

Normal users may receive:

- plain-language performance explanations
- their own connector/file/memory results
- support ticket creation/status where enabled

Normal users must not receive raw internal code reasoning, private repo diagnostics, global usage, global support ticket views, or raw internal telemetry.

## Latency Investigation Protocol

When investigating slow turns, inspect receipt data before guessing.

Primary fields:

```text
latency_trace
phase_timings
latency_category_totals
latency_budget
proactivity_policy
hydration_policy
tool_step_timings
tools_used
llm_call_count
active_context_tokens
```

The goal is to identify the actual cost center:

```text
LLM initial call
LLM recall after tool
pre-LLM DB/connector gather
history compression
memory ranking
continuity build
prompt build
tool/MCP execution
persistence/aftermath
```

## Normal-User Aria Continuity Lane

The normal-user Aria experience must preserve user trust.

Rules:

- Do not expose raw backend details like `Not your session` to normal users.
- Do not blame the model when the request failed due to session/auth/resource state.
- Preserve draft text and attachment UI state on failed sends.
- Uploaded images/files must be clearly associated with the chat turn before claiming Aria can see them.
- Conversation-local visual summaries are allowed.
- Permanent memory promotion must not be changed unless Michael explicitly assigns that lane.

## Housecleaning Direction

Large orchestration files should be reduced by behavior-preserving extraction.

Primary future extraction targets:

```text
backend/app/services/chat_tool_loop.py
backend/app/services/chat_receipt_builder.py
backend/app/services/chat_context_loader.py
backend/app/services/chat_preflight.py
backend/app/services/chat_aftermath.py
```

Do not delete features as a cleanup shortcut.

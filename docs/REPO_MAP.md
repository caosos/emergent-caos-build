# CAOS Repository Map

Purpose: make the repo searchable, listable, and inspectable by AI agents and humans without relying on guesswork.

## Top-Level Layout

```text
backend/       Backend API, services, data models, connectors, diagnostics
frontend/      React UI, chat surface, admin surfaces, settings, panels
memory/        Memory-related artifacts and supporting materials
tests/         Test files and smoke checks
test_reports/  Test output and reports
docs/          Architecture maps, agent-readable documentation, CCE proposal
```

## Architecture / proposal docs

```text
docs/CCE_CAOS_CARE_ENGINE_PROPOSAL.md       CAOS Council Engine proposal and CAOS Care CCE-lite integration direction
docs/LATENCY_AND_TURNTRACE.md              Hydration, proactivity, latency, and receipt diagnosis
docs/REPO_MAP.md                           This repository map
```

CCE search terms:

```text
CCE, CAOS Council Engine, council mode, verified mode, verifier, critic, risk gate, source posture, bias framing, CCE-lite, CAOS Care trust layer
```

## Backend Hotspots

### Primary orchestration

```text
backend/app/services/chat_pipeline.py
```

Role:

- Main chat turn coordinator.
- Loads session/profile.
- Saves user and assistant messages.
- Resolves runtime provider/model.
- Applies hydration and proactivity policy.
- Builds context and prompt.
- Runs LLM call and tool/MCP loops.
- Builds receipts, summaries, seeds, engine usage, and aftermath tasks.

Housecleaning direction: keep as orchestration spine only. Extract large responsibilities into focused modules.

CCE note: future CCE runtime work should not be bolted directly into `chat_pipeline.py` as a new God-file responsibility. Add focused modules/contracts for mode selection, verifier passes, council worker roles, and CCE receipts.

### Context and memory

```text
backend/app/services/context_engine.py
backend/app/services/continuity_service.py
backend/app/services/memory_worker_service.py
backend/app/services/global_info_service.py
backend/app/services/memory_extractor.py
```

Search terms:

```text
memory rank, structured_memory, thread_summaries, context_seeds, lane workers, continuity packet, global cache
```

### Hydration / proactivity / surface awareness

```text
backend/app/services/hydration_policy.py
backend/app/services/proactivity_policy.py
backend/app/services/surface_registry.py
```

Roles:

- `hydration_policy.py`: decides what context/tools should be loaded for the current turn.
- `proactivity_policy.py`: decides which departments should wake based on user intent.
- `surface_registry.py`: maps UI/capability surfaces and admin/user boundaries.

Search terms:

```text
hydration mode, wake departments, tools_allowed, connector_tools_allowed, admin surfaces, support tickets, memory console
```

CCE note: mode selection should align with hydration/proactivity rather than waking all departments on every turn. CCE modes should preserve the existing principle: right context, right time, right reason.

### Latency / receipts / telemetry

```text
backend/app/services/turn_trace.py
backend/app/services/artifact_builder.py
backend/app/services/token_meter.py
```

Roles:

- `turn_trace.py`: request-local forensic latency ledger.
- `artifact_builder.py`: persists receipts, summaries, seeds.
- `token_meter.py`: estimates/records token usage.

Search terms:

```text
TurnTrace, latency_trace, phase_timings, latency_category_totals, latency_budget, step_timings, receipt
```

CCE receipt fields should eventually include mode, worker roles, verifier result, contradictions, safety flags, source posture, confidence, final gate decision, cost estimate, and latency.

### Runtime / model selection

```text
backend/app/services/runtime_service.py
backend/app/services/model_catalog.py
```

Search terms:

```text
provider, model, context_window, OpenAI, Claude, Gemini, temperature
```

CCE note: CCE should remain provider-agnostic. Model choices are implementation details selected by policy, cost, context window, tool capability, and trust requirements.

### Tools / connectors

Likely locations:

```text
backend/app/services/aria_tools.py
backend/app/services/aria_tools_google.py
backend/app/services/aria_tools_obsidian.py
backend/app/services/aria_tools_slack.py
backend/app/services/aria_tools_messaging.py
backend/app/services/mcp_client.py
backend/app/routes/connectors.py
```

Search terms:

```text
TOOL, MCP_CALL, Gmail, Drive, Calendar, GitHub, Slack, Obsidian, Twilio, Telegram, connector tools
```

### Support tickets / diagnostics / admin

Likely locations:

```text
backend/app/routes/support.py
backend/app/services/aria_diagnostics.py
```

Search terms:

```text
FILE_TICKET, support ticket, query_receipts, profile_session, engine_usage, diagnostics
```

## Frontend Map

Primary frontend root:

```text
frontend/src
```

Search for visible UI strings when exact paths are unknown:

```text
Response latency
latency_ms
receipt
Welcome to CAOS
Memory Console
Admin Dashboard
Admin Docs
Support Tickets
Engine
Agent Swarm
Search this thread
```

Potential UI targets:

- Chat message bubble / assistant response card.
- Latency pill below assistant message.
- Admin dashboard / system console.
- Settings drawer.
- Memory console.
- Files / Photos / Links side panels.

Future CCE UI targets:

- Mode selector: Fast / Verified / Council / Lockdown.
- Receipt popover: why this mode was selected, verifier result, risk flags, source posture, cost, latency.
- Admin-only council diagnostics.
- Normal-user plain-language confidence and verification summary.

## Current Known PR Stack

```text
PR #1: fix/chat-hydration-gates-v1
  Goal: stop overhydration and keep departments/tools on standby unless relevant.

PR #2: fix/surface-registry-v1
  Goal: add surface registry and proactivity policy so Aria knows which cockpit surfaces/capabilities exist.

PR #3: fix/turntrace-ledger-v1
  Goal: add TurnTrace forensic latency ledger and persist latency receipt fields.
```

## Future Housecleaning Extraction Targets

Do not delete capability. Extract large mixed-responsibility code into focused modules.

Recommended order:

```text
1. backend/app/services/chat_tool_loop.py
   Extract tool scan, tool execution, MCP call, and LLM recall loop.

2. backend/app/services/chat_receipt_builder.py
   Extract receipt/token/lineage/artifact/engine usage construction.

3. backend/app/services/chat_context_loader.py
   Extract history fetch, compression, memory rank, continuity gather.

4. backend/app/services/chat_preflight.py
   Extract setup, profile/session load, quota, runtime resolution.

5. backend/app/services/chat_aftermath.py
   Extract persistence, lane worker rebuild, memory extraction scheduling.
```

Potential future CCE extraction targets once runtime work begins:

```text
backend/app/services/cce_policy.py
backend/app/services/cce_roles.py
backend/app/services/cce_verifier.py
backend/app/services/cce_receipt_builder.py
backend/app/services/cce_orchestrator.py
```

## Admin vs User Boundary

Admin-only:

```text
raw TurnTrace
repo/code diagnostics
admin docs
admin dashboard
global support tickets
engine spend/global usage
internal connector timing analysis
system architecture reasoning
raw CCE worker outputs / council diagnostics
```

User-available:

```text
their own files/photos/links
their own memory console if enabled
their own connector outputs
plain-language performance explanations
plain-language verification/confidence summary where enabled
support ticket creation/status where enabled
voice/settings/thread surfaces
```

## Search Recipes For Agents

Use these exact search strings if broad listing fails:

```text
TurnTrace latency_trace phase_timings
Response latency latency_ms receipt
hydration_policy tools_allowed connector_tools_allowed
proactivity_policy wake_departments
surface_registry Admin Dashboard Support Tickets
FILE_TICKET support ticket
MCP_CALL TOOL_RESULT aria_tools
structured_memory rank_memories context_seeds thread_summaries
CCE CAOS Council Engine verified mode council mode verifier risk gate
CCE-lite CAOS Care trust layer human escalation receipt
```

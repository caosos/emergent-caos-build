# Latency, Hydration, Proactivity, and TurnTrace

This document explains the CAOS latency architecture for humans and AI agents.

## Core Principle

Latency optimization must not remove capability.

Correct goal:

```text
right context
right time
right reason
measured cost
receipt-backed diagnosis
```

Incorrect goal:

```text
remove tools
remove connectors
remove memory
hide diagnostics
```

## Three-Layer Stack

### 1. Hydration Policy

File:

```text
backend/app/services/hydration_policy.py
```

Purpose:

- Decides how much context to load.
- Keeps history, cross-thread context, lane workers, global info, tool prompts, and connector tools on standby unless relevant.
- Prevents every department from showing up to every meeting.

Important receipt fields:

```text
hydration_policy
hydration_policy.mode
hydration_policy.history_token_budget
hydration_policy.use_cross_thread
hydration_policy.use_lane_workers
hydration_policy.use_global_info
hydration_policy.use_tool_prompt
hydration_policy.use_connector_tools
```

### 2. Proactivity Policy

File:

```text
backend/app/services/proactivity_policy.py
```

Purpose:

- Determines user intent and which departments should wake.
- Enables proactive diagnostics without loading everything on every turn.

Important receipt fields:

```text
proactivity_policy
proactivity_policy.primary_intent
proactivity_policy.wake_departments
proactivity_policy.allow_tools
proactivity_policy.allow_connectors
```

### 3. TurnTrace

File:

```text
backend/app/services/turn_trace.py
```

Purpose:

- Records a forensic per-turn latency ledger.
- Answers what added time, when it added time, and why relevant systems woke up.

Important receipt fields:

```text
latency_trace
phase_timings
latency_category_totals
latency_budget
tool_step_timings
tools_used
llm_call_count
```

## Why Step Timings Alone Were Not Enough

A single response latency number can only say:

```text
The turn ended at 16.7s.
```

TurnTrace can say:

```text
history_compress added 220ms
memory_rank added 80ms
pre_llm_gather added 1.1s
llm_initial added 8.9s
tool execution added 1.4s
llm_recall.1 added 4.2s
```

This turns latency from a mystery into a receipt-backed diagnosis.

## Typical Latency Cost Centers

```text
setup/profile load
quota check
history fetch
history compression
memory ranking
pre-LLM DB/connector gather
continuity build
prompt build
attachment file content build
LLM prepare
initial LLM call
tool scan
tool/MCP execution
LLM recall after tool
ticket marker parsing
assistant message save
post-LLM reads
token receipt build
artifact/receipt build
background aftermath
```

## Tool / Connector Turns

Tool turns can require multiple model calls:

```text
initial LLM call
→ tool marker emitted
→ tool executes
→ tool result fed back
→ LLM recall generates final response
```

So a slow tool turn may be caused by:

```text
tool execution itself
LLM recall after tool
tool result payload size
connector preflight/gather
model-side latency
```

Do not assume the tool is the bottleneck. Inspect `tool_step_timings`, `phase_timings`, and `latency_category_totals`.

## Latency Budget Concept

TurnTrace classifies rough lane budgets:

```text
fast_or_single_llm: target 10s
single_tool: target 15s
multi_tool: target 20s+ depending on iterations
```

The field:

```text
latency_budget
```

contains:

```text
lane
target_ms
actual_ms
exceeded
over_by_ms
tool_iterations
active_context_tokens
context_pressure
```

## Admin vs Normal User Behavior

Admin users may see internal diagnostics:

```text
raw TurnTrace
phase timings
repo/code path reasoning
connector timing internals
PR/branch diagnostics
system architecture analysis
```

Normal users should receive plain-language explanations:

```text
That response took longer because I used extra tools/context for your request.
I can file a support ticket if this keeps happening.
```

Normal users should not receive raw internal telemetry or code-path analysis.

## Desired UI Surface

The latency pill below assistant messages should become clickable.

Example visible pill:

```text
16.7s
```

Admin popover target:

```text
Response latency — 16.7s
Budget: 15.0s — exceeded by 1.7s
Top contributors:
1. llm_initial — 8.9s
2. llm_recall.1 — 4.2s
3. pre_llm_gather — 1.1s
Hydration: tool
Proactivity: latency_diagnostic
Tools: web_fetch
[View full trace]
```

Normal user popover target:

```text
This response took longer because extra context/tools were used.
```

## Investigation Protocol

When asked why a turn was slow:

1. Query or inspect the latest receipt.
2. Read `latency_budget`.
3. Sort `phase_timings` descending.
4. Check `latency_category_totals`.
5. Check `tools_used` and `tool_step_timings`.
6. Check hydration and proactivity policy.
7. Explain the largest true cost center.
8. Recommend or patch only after evidence.

## Example Diagnosis

```text
I checked the latest receipt.
The slowest phase was llm_initial at 8.7s.
pre_llm_gather was 420ms, memory_rank was 60ms, and history_compress was 110ms.
No tool calls ran.
This was model-side latency, not hydration or memory bloat.
```

# CCE — CAOS Council Engine Proposal

Status: proposal / architecture direction  
Scope: CAOS core engine, reusable by CAOS Care and future verticals  
Primary decision: build the council/verifier capability as a CAOS engine layer, then expose a lighter care-safe profile inside CAOS Care.

## Executive decision

CAOS should treat multi-model council orchestration as a core engine capability, not as a vendor feature, marketing add-on, or one-off prompt trick.

The proposed engine name is:

```text
CCE = CAOS Council Engine
```

CCE is the governed trust layer that lets CAOS move beyond one model answering alone. It gives CAOS a repeatable way to route serious work through independent workers, contradiction checks, bias/framing checks, source review, synthesis, verification, and receipts.

The immediate implementation should not start with the biggest possible council. The immediate implementation should define the engine contract and add a small mode ladder:

```text
Fast Mode      -> one model, low-risk, low-cost
Verified Mode  -> one model plus verifier / critic
Council Mode   -> multiple independent workers plus synthesizer plus verifier
Lockdown Mode  -> no AI final answer; human escalation only
```

CAOS Care should use CCE-lite first. Full Council Mode belongs in admin, policy, incident review, product research, and complex decision support. Resident-facing and staff-facing care flows need speed, clarity, audit logs, and escalation more than a heavy multi-model debate on every turn.

## Why this belongs in CAOS

CAOS is already structured around governed context, memory, tools, routing, receipts, diagnostics, and user-owned rules. CCE is the natural next engine layer because it turns those primitives into verified decision flow.

Current CAOS primitives that CCE should build on:

- model/provider routing;
- context hydration policy;
- tool and connector gating;
- memory and continuity packets;
- receipts and lineage;
- admin diagnostics;
- support-ticket and escalation surfaces;
- lane workers and future specialized agents.

CCE should not replace those systems. It should coordinate them.

## Core doctrine

One model is a voice. A governed council is a system.

CCE exists to reduce unchecked model failure modes:

- confident wrong answers;
- missing assumptions;
- ideological or emotional framing;
- weak source selection;
- overbroad conclusions;
- unsafe action recommendations;
- undocumented reasoning paths;
- hidden uncertainty;
- one-provider dependence.

The goal is not to claim perfect neutrality. The goal is:

```text
bias-detected
source-grounded
contradiction-checked
risk-gated
receipt-backed
audit-visible
human-governed
```

## CCE is not a political system

CCE is not a party-position engine. It should not be tuned to produce left-wing or right-wing answers.

For civic, policy, government, and public-trust use cases, CCE should explicitly separate:

- primary facts;
- source quality;
- legal/procedural constraints;
- left/right/center framing;
- opinion versus reporting;
- consensus versus dispute;
- confidence versus uncertainty;
- recommended next verification steps.

The correct output is not "balanced noise." The correct output is a clear distinction between what is known, what is claimed, what is disputed, and what still needs verification.

## Engine roles

CCE should support a configurable role set. Not every turn wakes every role.

### 1. Router / dispatcher

Classifies the request and selects the mode.

Inputs:

- user intent;
- lane / surface;
- risk level;
- required tools;
- needed context;
- cost/latency budget;
- admin versus normal-user boundary.

Outputs:

- `cce_mode`;
- selected worker roles;
- allowed tools;
- required receipts;
- stop conditions.

### 2. Primary worker

Produces the initial useful answer or plan.

Typical uses:

- simple explanation;
- normal assistant response;
- staff-facing summary;
- first draft;
- initial research plan.

### 3. Research worker

Finds and summarizes evidence when sources matter.

Rules:

- prefer primary sources;
- separate direct evidence from commentary;
- record source gaps;
- do not inflate certainty.

### 4. Opposition / red-team worker

Attacks the answer.

Questions:

- What is missing?
- What assumption is doing too much work?
- What would a critic say?
- What could be unsafe, misleading, or incomplete?
- What would change the conclusion?

### 5. Bias / framing worker

Checks language, source selection, and conclusion framing.

This worker should not enforce artificial centrism. It should identify loaded wording, one-sided source pools, cherry-picked evidence, and hidden normative assumptions.

### 6. Domain safety worker

Specialized gate for high-risk lanes.

Examples:

- CAOS Care: resident safety, privacy, human oversight, no autonomous medical authority.
- Government/civic: law, process, public record, auditability.
- Finance: no unsupported investment certainty.
- Health: no diagnosis or treatment authority without proper scope.

### 7. Synthesizer

Builds the final answer from worker outputs.

It should preserve:

- strongest facts;
- material disagreements;
- source limits;
- confidence level;
- action boundaries;
- next safe step.

### 8. Verifier / gatekeeper

Final pass before user-visible output or system action.

It decides:

- answer allowed;
- answer allowed with caveats;
- ask for missing information;
- escalate to human;
- block action;
- create support/incident/task ticket;
- require admin review.

## Mode ladder

### Fast Mode

Use when being slightly wrong is low consequence and speed matters.

Examples:

- casual explanation;
- UI help;
- simple formatting;
- non-sensitive brainstorming;
- basic task classification.

Shape:

```text
router -> primary model -> response + lightweight receipt
```

### Verified Mode

Use when the answer matters, but full council is unnecessary.

Examples:

- family message draft;
- staff note summary;
- maintenance prioritization;
- resident comfort request;
- policy-adjacent explanation;
- admin support question.

Shape:

```text
router -> primary model -> verifier/critic -> final response + receipt
```

### Council Mode

Use when error cost, ambiguity, ideology, source quality, or strategic impact is high.

Examples:

- government/policy analysis;
- serious incident review;
- business-critical architecture decision;
- disputed family/staff communication;
- legal/clinical/regulatory-adjacent reasoning;
- product strategy;
- complex debugging/root-cause analysis.

Shape:

```text
router
  -> worker panel
  -> opposition / bias / safety checks
  -> synthesizer
  -> verifier
  -> final response + council receipt
```

### Lockdown Mode

Use when the system should not answer as authority.

Examples:

- emergency medical situation;
- autonomous clinical/legal decision request;
- unsafe resident-care instruction;
- privacy boundary failure;
- destructive tool action without approval;
- missing required human confirmation.

Shape:

```text
router -> block/escalate -> receipt
```

## User/admin toggles

CCE should expose toggles as product controls, not as confusing model jargon.

Recommended controls:

```text
Speed vs verification
Source strictness
Political/source balance
Primary-source-only mode
Show disagreements
Show confidence
Show receipts
Escalate instead of answer
Use low-cost worker panel
Use premium worker panel
```

For normal users, these should be simple. For admins/builders, they can expose more detail.

## Source doctrine

CCE should prefer sources in this order:

1. Primary sources: statutes, court filings, official records, transcripts, raw data, original studies, direct statements.
2. Institutional sources: auditors, watchdogs, universities, standards bodies, regulators, official agencies.
3. Reputable reporting: clearly labeled as reporting and checked against primary evidence where possible.
4. Ideological/opinion sources: allowed when relevant, but labeled as framing or commentary.
5. Unverified claims: only surfaced as claims, never as established facts.

CCE should record source posture in the receipt:

```text
source_mode
primary_source_count
ideological_span
known_gaps
citation_quality
unverified_claims
```

## Receipt requirements

A CCE receipt should be machine-readable and admin-readable.

Minimum fields:

```text
cce_mode
worker_roles_used
models_used
provider_mix
reason_for_mode
risk_level
source_mode
claims_checked
contradictions_found
bias_or_framing_flags
safety_flags
human_escalation_required
confidence
cost_estimate
latency_ms
final_gate_decision
```

For CAOS Care, receipts must avoid leaking unnecessary private resident/staff/family data.

## CAOS Care integration decision

CAOS Care needs trust today, but it does not need the full CCE on every resident/staff interaction.

CAOS Care should use:

```text
CCE-lite = router + risk gate + verifier + receipt + human escalation
```

The care product should sell operational trust, not multi-model complexity.

What senior care needs first:

- resident heard;
- right staff notified;
- task/alert documented;
- family/staff communication cleaned up;
- unsafe medical/legal authority avoided;
- private data protected;
- leadership can inspect what happened.

CCE-lite supports that immediately.

Full CCE can be enabled later for:

- policy creation;
- serious incident review;
- family dispute summaries;
- regulatory/compliance research;
- architecture decisions;
- care workflow redesign;
- multi-source research.

## Proposed CAOS implementation phases

### Phase 0 — Documentation contract

Add this proposal and matching CAOS Care CCE-lite proposal.

No runtime behavior change.

### Phase 1 — Data contract

Add internal schemas/constants for:

```text
cce_mode
risk_level
worker_role
cce_receipt
final_gate_decision
```

No multi-model calls yet.

### Phase 2 — Verified Mode

Add one verifier/critic pass behind an admin or feature flag.

Suggested first path:

```text
primary answer -> critic/verifier -> final answer
```

Persist verification receipt fields.

### Phase 3 — Care-safe CCE-lite

Expose CCE-lite to CAOS Care flows:

- resident request classification;
- staff task notes;
- family update drafts;
- incident/handoff summaries;
- privacy/safety gate.

### Phase 4 — Council Mode

Add configurable worker panels for admin/research/civic/architecture workflows.

Start with small panels and clear budgets.

### Phase 5 — Builder/admin UX

Expose toggles and receipt views:

- mode selected;
- why selected;
- what was checked;
- what was blocked;
- source posture;
- cost and latency.

## Non-goals for first build

Do not start by building:

- a giant agent swarm;
- a full government product;
- autonomous medical logic;
- complex resident-facing model controls;
- provider-specific lock-in;
- unverifiable neutrality claims;
- heavy panels on every chat turn.

## Acceptance criteria

CCE is real when CAOS can answer these questions for an important output:

```text
Why did this turn use this mode?
Which model(s) worked on it?
What did the verifier check?
What contradictions or risks were found?
What sources supported the answer?
What was blocked or escalated?
What confidence was assigned?
Where is the receipt?
```

CAOS Care CCE-lite is real when staff/admin can answer:

```text
What did the resident/staff/family ask?
What action was taken?
Who was notified?
Was a human required?
Was private or medical-adjacent content protected?
What receipt proves the flow?
```

## Final product position

CCE is the trust engine.

CAOS is the governed operating system.

CAOS Care is the senior-care product using the engine in a practical, fast, human-supervised way.

The platform should not be valuable because it merely has AI. It should be valuable because it makes AI behave like it is being audited before it speaks or acts.

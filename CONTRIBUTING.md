# Contributing to CAOS

CAOS is a working prototype and active rebuild target. Contributions, forks, criticism, issue reports, architecture review, and implementation ideas are welcome.

## Best Ways To Help

Useful feedback includes:

- memory architecture;
- context hydration and ranking;
- MCP/tool loop safety;
- model routing and cost control;
- worker-agent orchestration;
- diagnostics and receipts;
- frontend/admin UX;
- test coverage;
- modular extraction strategy;
- clean rebuild strategy.

## Before Commenting Or Opening A Pull Request

Please inspect the relevant source first.

Recommended starting files:

1. `README.md`
2. `AGENTS.md`
3. `docs/REPO_MAP.md`
4. `docs/LATENCY_AND_TURNTRACE.md`
5. `backend/app/services/chat_pipeline.py`
6. `backend/app/services/hydration_policy.py`
7. `backend/app/services/turn_trace.py`
8. `frontend/src`

## Current Project Reality

This repository is a prototype/reference implementation. Some code may be platform-coupled to Emergent. The clean rebuild direction is tracked separately in:

- https://github.com/caosos/linode-repo

Please distinguish:

- working prototype behavior;
- code that should be salvaged;
- code that should be redesigned;
- planned future architecture;
- private product implementation.

## CAOSCare Boundary

CAOSCare is a private product direction built around CAOS architecture.

Do not publish or request:

- private CAOSCare implementation code;
- real resident/staff/facility data;
- private deployment credentials;
- sensitive operational screenshots/logs;
- facility-specific workflows that have not been intentionally sanitized.

Public concept-level CAOSCare discussion is fine.

## Pull Request Guidance

Preferred PRs are bounded and explain exactly what changed.

Good PR types:

- documentation cleanup;
- test improvements;
- small bug fixes;
- modular extraction proposals;
- diagnostic/receipt improvements;
- safety/privacy improvements;
- build/dependency cleanup.

Avoid:

- huge rewrites without a migration plan;
- unrelated refactors;
- silent behavior changes;
- deleting capability without replacement;
- adding secrets or private data;
- claiming something works without evidence.

## AI-Agent Contributions

If you use an AI coding agent:

- inspect before writing;
- cite files inspected in the PR body;
- state exactly what changed;
- include acceptance criteria;
- include test or validation notes;
- stop on uncertainty instead of inventing facts.

## License

CAOS is released under the MIT License unless a specific file states otherwise.

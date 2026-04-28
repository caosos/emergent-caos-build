# CAOS Agent Tooling Field Notes

Repo: `caosos/emergent-caos-build`

Scope: these are execution observations discovered while using the GitHub connector against this repository. This document supplements `AGENTS.md`; it does not replace branch discipline or preserve-list rules.

## 1. GitHub code search may return false negatives

Observed: repo code search may be unavailable, incomplete, or stale.

Effect: searches for valid repo terms can return no results even when files or symbols exist.

Correction: do not treat failed code search as proof that a file, route, component, or symbol does not exist.

Fallback inspection path:

```text
README.md
AGENTS.md
docs/REPO_MAP.md
docs/LATENCY_AND_TURNTRACE.md
known direct file paths
runtime screenshots / request evidence as clues, then source verification
```

## 2. Directory/tree browsing through the connector may be partial

Observed: fetching GitHub tree/directory URLs can return incomplete directory content.

Effect: directory inspection may not be reliable enough to map the repo by itself.

Correction: prefer documented repo maps and direct known-path fetches over broad directory listing when connector browsing is incomplete.

## 3. Raw GitHub API tree URLs may be rejected by the connector

Observed: some `api.github.com` tree/list URLs may be rejected as invalid by the connector.

Correction: do not rely on raw GitHub API tree URLs inside the connector unless the specific tool supports them.

## 4. Branch creation state must be verified before writing

Observed: a write attempt with no explicit branch may fail or behave differently than expected.

Correction before any write:

```text
1. Create or confirm the active branch.
2. Verify the branch exists.
3. Write only to that branch.
4. Compare branch against main after commit.
5. If branch state is uncertain, stop.
```

## 5. Stacked work must compare against the immediate parent branch

Observed: comparing an active branch directly against `main` can include prior stacked work and exaggerate the diff.

Correction: for stacked work, compare both:

```text
active branch vs main
active branch vs immediate parent branch
```

## 6. Current PR stack state matters before new work

Observed: the repo may have stacked active work already in progress.

Correction: a new lane that depends on prior branch fields or behavior should branch from the relevant parent branch, not automatically from `main`.

## 7. Connector failures should be treated as receipts

Observed failure categories:

```text
incomplete code search indexing
partial directory fetch
raw API URL rejection
branch/write ambiguity
failed direct file lookup for wrong guessed paths
```

Correction: report connector failures as execution facts. Do not hide them or imply inspection succeeded.

## 8. Direct known-path fetch is more reliable than broad search

Observed: search can fail while direct fetch of known files succeeds.

Correction: when repo docs name a path, fetch that path directly before relying on search.

## 9. Screenshots can expose real runtime paths before search does

Observed: runtime screenshots can reveal component names, request URLs, status codes, and stack initiators.

Correction: use screenshot evidence to guide repo inspection, then verify against source files before patching.

## 10. Runtime bugs may cross frontend/backend boundaries

Observed: visible frontend failures may originate from:

```text
session ownership state
request classification
upload association
backend schema shape
object storage behavior
model/provider capability mismatch
```

Correction: do not assume “frontend bug” or “backend bug” from UI symptoms alone. Inspect the path end-to-end before writing.

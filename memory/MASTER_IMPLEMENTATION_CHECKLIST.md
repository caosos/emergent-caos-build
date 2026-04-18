# CAOS Master Implementation Checklist

Status: Living contract document
Owner: Aria build process + user direction
Update rule: This file should be updated whenever a phase item is completed, re-scoped, blocked, or reprioritized.

## Status Legend
- [x] Complete
- [~] In progress
- [ ] Not started
- [!] Blocked / dependent

## Core Product Contract
CAOS is not a generic chatbot. It is a persistent cognitive operating system with:
- a collapsible sidebar and clean work surface
- fast, lean active context with sanitization + rehydration
- cross-thread continuity without context bloat
- editable persistent memory and personal facts bins
- live working context visibility derived from actual token usage
- reusable cached/global knowledge to avoid unnecessary compute
- action surfaces, logs, receipts, and eventually life-aware assistance

---

## Phase 1 — Core Shell Parity
Goal: Make the main shell structurally match the intended CAOS operating experience.

### 1.1 Shell architecture
- [x] Collapsible sidebar that is visible on entry and hideable for a clean surface
- [~] Remove duplicate/competing top identity/menu patterns
- [~] Canonical user/name/avatar dropdown with side-opening option panels
- [~] Compact top bar aligned to screenshot direction

### 1.2 Chat surface parity
- [~] `/chat` layout closer to screenshot reference
- [~] Denser message cards with inline action controls
- [~] White/slim bottom composer parity
- [x] Overlay-style previous threads behavior where appropriate
- [~] Compact right search/context strip parity

### 1.3 First-run / welcome
- [ ] `/Welcome` landing with starfield hero and feature tiles
- [ ] Guided multi-step onboarding tour modal
- [ ] `Take the Tour` / `Sign In` / `Continue as Guest` flow

### 1.4 Supporting shell surfaces
- [ ] Richer files / photos / links surfaces
- [ ] Deeper profile/settings drawer parity
- [ ] Cleaner WCW visibility in the shell header/surfaces

---

## Phase 2 — Memory Engine Foundation
Goal: Keep active reasoning fast while continuity feels effectively endless.

### 2.1 Context discipline
- [ ] Hard-bounded hot working context
- [ ] Sanitization pipeline for duplicates, low-signal turns, stale instructions
- [ ] Rehydration order contract (thread → lane → facts → global bin)
- [ ] Cost-governed context budgets per turn

### 2.2 Memory layers
- [~] Subject bins / lanes
- [~] Receipts / summaries / seeds
- [~] Cross-thread worker snapshots
- [ ] Personal facts bin
- [ ] Editable persistent memory controls
- [ ] Global info bin / lookup reuse cache

### 2.3 WCW / token governance
- [ ] Live WCW monitor derived from actual token usage inside the session, not rough placeholders
- [ ] Track sent tokens, received tokens, and currently active packet tokens per session
- [ ] Distinguish thread total vs active context vs compressed memory vs rehydrated memory
- [ ] Explain what was kept, dropped, compressed, and reused

### 2.4 Thread intelligence
- [ ] Auto-title new threads within first 1–3 useful turns
- [ ] Better retrieval ranking and bin governance
- [ ] Controlled cross-thread hydration with clarity options

---

## Phase 3 — Provider Portability
Goal: CAOS works above any single inference provider.

### 3.1 Provider routing
- [~] Universal Key path for OpenAI / Claude / Gemini
- [ ] BYO-provider credential attachment flow
- [ ] Grok/xAI adapter path
- [ ] Runtime provider vault / controls

### 3.2 Model policy
- [ ] Task-to-model routing policy
- [ ] Chat / image / voice routing policies
- [ ] User-facing model/provider controls that remain simple

### 3.3 Image generation action
- [ ] `Create Image` as first-class action
- [ ] Experiment path for Gemini image generation vs OpenAI image generation

---

## Phase 4 — Actions + Operating System Layer
Goal: Move CAOS from “chat” to “do”.

### 4.1 Action surfaces
- [ ] Work-list capture
- [ ] Quick task / note action from composer or shell
- [ ] Commitments and reminders
- [ ] Bill / obligation prompts with explicit permissions

### 4.2 Observability
- [ ] Error logs
- [ ] System console
- [ ] Tool receipts / action traces
- [ ] Failure / retry / skip reasoning surfaces

### 4.3 Permissions
- [ ] Explicit account and action permission model
- [ ] “Would you like me to handle this?” confirmation loop

---

## Phase 5 — Knowledge Workspace / Second Brain
Goal: Build the Obsidian-plus layer inside CAOS.

### 5.1 Notes core
- [ ] Quick note capture
- [ ] Voice-to-note flow
- [ ] Work-list placement for captured notes/tasks
- [ ] Structured note storage

### 5.2 Knowledge graph
- [ ] Bidirectional links
- [ ] Auto-linking foundation
- [ ] Graph view
- [ ] Knowledge cards / relation surfaces

### 5.3 Memory views
- [ ] Personal memory view
- [ ] Project memory view
- [ ] Global knowledge bin view

---

## Phase 6 — Time-Aware Living Assistant Layer
Goal: Make Aria a persistent, life-aware operating companion.

### 6.1 Time awareness
- [ ] Today / this week / overdue awareness
- [ ] Recurring obligations
- [ ] Active / resting / unavailable state awareness

### 6.2 Life continuity
- [ ] Long-horizon personal continuity
- [ ] Cross-thread obligation tracking
- [ ] Proactive suggestions tied to context and permissions

---

## Phase 7 — Connectors
Goal: Connect CAOS to the user’s external systems and tools.

### 7.1 Core connectors
- [ ] Google Workspace / Gmail / Drive / Calendar
- [ ] GitHub

### 7.2 Future connectors
- [ ] Home automation / utility / payment connectors where appropriate
- [ ] External knowledge sync

---

## Current Priority Order
1. Finish Phase 1 shell parity correctly
2. Deepen Phase 2 memory governance and cost discipline
3. Complete Phase 3 provider portability and BYO-provider flow
4. Build Phase 4 action/OS layer
5. Build Phase 5 knowledge workspace
6. Build Phase 6 life-aware assistant layer
7. Add Phase 7 connectors

## Immediate Next Contract Slice
- [~] Remove the wrong top menu pattern and make one canonical identity/menu control
- [~] Tighten the sidebar behavior and hierarchy to match the intended CAOS shell
- [~] Start `/chat` visual parity pass before moving deeper into the welcome flow

## Current Note
- The current chat strip exposes working-packet information using existing receipt/context estimates. True token-derived WCW accounting remains a Phase 2 contract item and is not considered complete yet.

# CAOS System Blueprint v1

Last Updated: 2026-04-18
Status: Replatform in progress
Runtime: React frontend + FastAPI backend + MongoDB

## 0. Purpose

CAOS is not a chatbot product.

CAOS is a **permissioned personal operating intelligence** designed to:
- learn a user over time with consent
- maintain continuity across lanes, tasks, and life contexts
- act proactively when allowed
- support multimodal inputs and outputs
- specialize into domain copilots and role-specific agents
- preserve truth, memory boundaries, and user trust above presentation

This blueprint is the canonical reference for architecture, governance, terminology, active systems, planned systems, and troubleshooting discipline.

---

## 1. Core Product Thesis

CAOS is being built as a continuous intelligence layer for real life and real work.

Examples of target impact:
- mechanics and field technicians
- 911 dispatch and live troubleshooting
- teachers with differentiated assistants for each student
- accessibility, including AI vision + glasses and assisted perception
- daily memory support, reminders, and proactive organization
- connector-backed action across Gmail, Drive, Workspace, GitHub, and home systems

The system must be able to evolve from single-thread conversation into:
- multi-lane intelligence
- multimodal operation
- domain specialization
- proactive permissioned action
- long-horizon user learning

---

## 2. Governing Principles

### 2.1 Truth over appeasement
The system should never pretend functionality exists when it does not.

### 2.2 Trust first
Every memory, action, connector, and proactive behavior must be earned through explicit permission and understandable boundaries.

### 2.3 Modularity over monoliths
Preferred file size: under 200 lines.
Hard ceiling target: 400 lines.

### 2.4 Session isolation first
`session_id` is the active isolation boundary for the current replatform.

### 2.5 Lanes and planes later, not forgotten
The current implementation is session-scoped, but the blueprint is intentionally designed to grow into multi-lane and multi-plane memory.

### 2.6 TSB discipline
Every meaningful failure, regression, trap, or recurring bug must be logged in the TSB log.

---

## 3. Current Runtime Stack

### Frontend
- React
- modular shell components under `frontend/src/components/caos/`
- current shell focus: persistent rail, centered canvas, drawers, richer message bubbles

### Backend
- FastAPI
- modular services under `backend/app/services/`
- MongoDB storage

### AI Models currently wired
- chat: OpenAI `gpt-5.2`
- text-to-speech: `tts-1-hd`
- speech-to-text: `whisper-1`

---

## 4. Active System Map

### 4.1 Active shell surfaces
- persistent left rail
- recent thread list
- centered chat canvas
- composer with text, file upload, and microphone input
- floating search drawer
- profile drawer
- files/artifacts drawer
- receipt card
- continuity card
- richer bubble controls

### 4.2 Active backend contracts
- sessions
- messages
- structured memory
- context preparation
- chat turn orchestration
- artifact retrieval
- continuity retrieval
- file upload/link/download
- backend TTS
- backend STT

---

## 5. Canonical Request Pipeline

Current chat flow:

1. load session by `session_id`
2. ensure / create user profile
3. store user message
4. load session history
5. sanitize history
6. compress history
7. rank structured memory against current query
8. build system prompt
9. call LLM
10. store assistant message
11. write receipt
12. write summary
13. write seed
14. update session preview/summary
15. return reply + receipt + WCW estimate

Current shorthand:

`ingest -> sanitize -> compress -> retrieve -> inject -> reply -> receipt -> lineage`

---

## 6. Data Model — Current

### Sessions
Purpose: thread boundary and current isolation container

### Messages
Purpose: canonical ordered conversation history per session

### User Profiles
Purpose: user-level identity and structured memory

### Receipts
Purpose: evidence of what retrieval/injection happened for a turn

### Thread Summaries
Purpose: compact continuity summaries for future rehydration

### Context Seeds
Purpose: compressed continuity anchors for future chainable rehydration

### User Files
Purpose: uploaded files, photos, and saved links

---

## 7. Data Model — Planned Expansion

These are planned, not fully implemented:

### Lanes
Separate memory/work domains such as:
- home
- work
- mechanical troubleshooting
- dispatch
- education
- medical
- administrative

### Planes / bins
Different memory and tool layers, such as:
- explicit saved memory
- task state
- continuity state
- connector state
- domain knowledge packs
- accessibility state

### Agent families
Future CAOS will support multiple subordinate or specialized agents operating within permissioned lanes.

---

## 8. Continuity and Rehydration Model

Current continuity is still early-stage but real:
- receipts store what mattered in a turn
- summaries store compact turn-level continuity
- seeds store compressed continuity fragments
- lineage fields track previous receipt/summary/seed relationships

Planned next step:
- turn lineage into actual thread rehydration logic
- allow the system to reconstruct ongoing work over long horizons
- support campaign-style, project-style, and user-life continuity

---

## 9. Multimodal Model

### Active today
- text input
- file upload
- saved links
- backend TTS
- backend STT

### Planned next
- richer voice settings
- image understanding
- AI vision workflows
- wearable/glasses support concepts
- domain-specific camera and field troubleshooting surfaces

---

## 10. Connector Model

Connectors are not fully active yet, but they are core to the mission.

Target connector families:
- Gmail
- Google Drive
- Google Workspace
- GitHub
- home automation / devices
- task/calendar systems

Connector design rules:
- explicit permission
- auditable actions
- revocable access
- clear boundary between suggestion and action

---

## 11. Admin and Self-Inspection Plane

CAOS needs an **administrative account plane** that can inspect the system itself.

This does **not** mean every user should have platform-level code visibility.

### Admin-only capabilities planned
- read selected application code
- inspect architecture state
- reason about internal modules
- analyze regressions using TSB records
- inspect receipts, summaries, lineage, and continuity state

### Standard user capabilities planned
- use GitHub or connected repos they explicitly grant
- use connectors they authorize
- inspect their own memories, artifacts, and files
- not gain unrestricted platform code visibility

This self-inspection/admin plane is a blueprint requirement, not yet fully implemented.

---

## 12. UI Blueprint — Current Direction

The correct CAOS shell direction is:
- persistent left navigation rail
- open center canvas with breathing room
- lighter top bar
- smaller mobile-aware search
- fewer always-open utility panels
- richer message bubble behavior
- command-center style empty state

Avoid:
- duplicate navigation surfaces
- overly busy top bars
- dashboard overload
- exposing raw technical state without explanation

---

## 13. What Is Live vs Planned

### Live
- session isolation
- modular FastAPI backend
- shell with drawers and richer bubbles
- artifact lineage fields
- backend TTS/STT primitives
- files/links handling

### Partial
- shell parity with original CAOS screenshots
- continuity/rehydration
- artifact evidence depth
- voice UX fidelity

### Planned
- multi-lane memory
- multi-plane storage
- admin self-inspection plane
- connector ecosystem
- full proactive agentic behavior
- accessibility/vision surfaces
- domain-specialized copilots

---

## 14. Build Phases

### Phase A — Runtime replacement
Replace Base44/Deno constraints with a modular Python backend and React shell.

### Phase B — Continuity substrate
Receipts, summaries, seeds, lineage, rehydration.

### Phase C — Shell parity
Match the original CAOS UX truth surface with cleaner structure.

### Phase D — Permissions + connectors
Workspace, Gmail, Drive, GitHub, home automation.

### Phase E — Multi-lane intelligence
Parallel user-lane architecture and specialized sub-agents.

### Phase F — Multimodal and accessibility systems
Vision, glasses, field support, live troubleshooting, assistive perception.

---

## 15. Working Status for Team

Current project state is **real foundation, not finished product**.

What exists now is enough to prove:
- Python backend replatform is viable
- session-scoped continuity works
- artifacts and lineage can be stored
- shell fidelity can be evolved incrementally

What is not yet true:
- full CAOS parity
- full multi-lane intelligence
- full agentic orchestration
- full connector-backed proactive life integration

---

## 16. TSB Policy

Every material failure, regression, constraint, or trap gets a TSB record.

Each TSB entry should include:
- ID
- title
- date
- symptom
- impact
- root cause
- fix
- prevention rule

Canonical log file: `/app/memory/TSB_LOG.md`

# CAOS TSB Log

Troubleshooting Bulletins for the current replatform.

---

## TSB-001 — Session Isolation Must Be the First Invariant
Date: 2026-04-18

### Symptom
Early replatform risk of rebuilding UI before locking the isolation boundary.

### Impact
Could have caused memory mixing and architectural drift.

### Root Cause
CAOS continuity requirements were larger than a simple chat port.

### Fix
Locked `session_id` as the first invariant and built context preparation around it.

### Prevention
Never build higher-order continuity before isolation semantics are explicit.

---

## TSB-002 — Chat Pipeline 500 from Structured Memory Re-Parsing
Date: 2026-04-18

### Symptom
`POST /api/caos/chat` returned a 500 after the real shell started using the Python chat turn.

### Impact
Assistant replies failed in the live shell.

### Root Cause
`profile.structured_memory` already contained parsed `MemoryEntry` objects, but code attempted to unpack them again as mappings.

### Fix
Use the profile memory list directly instead of reparsing it.

### Prevention
At service boundaries, verify whether payloads are raw dicts or typed models before rebuilding them.

---

## TSB-003 — Receipt Math Did Not Reflect True Pre-Compression Size
Date: 2026-04-18

### Symptom
Receipt reduction values initially used compressed-message size as the before-state.

### Impact
Reduction telemetry could look misleading.

### Root Cause
Receipt calculation used the wrong baseline.

### Fix
Compute `estimated_chars_before` from original messages and expose injected memory chars separately.

### Prevention
Any observability metric must state what pre-state and post-state actually mean.

---

## TSB-004 — Clipboard Permission Could Crash the Bubble Action
Date: 2026-04-18

### Symptom
Copy action failed noisily when browser clipboard permission was denied.

### Impact
Poor UX and avoidable action failures.

### Root Cause
Clipboard writes were not wrapped with fallback handling.

### Fix
Catch permission failure and surface inline action status instead of throwing.

### Prevention
All browser capability APIs must fail gracefully.

---

## TSB-005 — Header Menu → Files Drawer Regression
Date: 2026-04-18

### Symptom
Clicking Files & Artifacts from the header menu did not open the drawer reliably.

### Impact
Navigation looked present but behaved inconsistently.

### Root Cause
Overlay/menu interaction and clipping made the click path unreliable.

### Fix
Reworked the header menu behavior and tested the Files path directly.

### Prevention
Every menu action must be included in regression UI tests, especially nested surface openers.

---

## TSB-006 — Profile Bootstrap 404 Noise
Date: 2026-04-18

### Symptom
Fresh identities triggered noisy profile lookup failures on shell load.

### Impact
Unnecessary error noise during bootstrap.

### Root Cause
Missing profile was treated as an exceptional condition instead of a valid first-load state.

### Fix
Return a default profile shape when no stored profile exists yet.

### Prevention
Bootstrap reads for optional user objects should fail soft when emptiness is a valid state.

---

## TSB-007 — Transcription Reliability Is Not Yet Good Enough for Long Spoken Input
Date: 2026-04-18
Status: Open

### Symptom
Long spoken input was not captured reliably enough.

### Impact
Loss of user trust and loss of important spoken context.

### Root Cause
Current microphone/transcription flow is still primitive and not yet robust for long-form speech.

### Current Mitigation
Keep STT path available as experimental groundwork, not trusted final capture.

### Prevention / Next Fix
Add robust recording UX, visible recording state, better chunk handling, retry-safe upload, and transcript confirmation before send.

---

## TSB-008 — Platform Composer Can Erase In-Progress User Input
Date: 2026-04-18
Status: External Platform Issue

### Symptom
User reported in-progress text being erased while continuing to type or add to a message.

### Impact
Severe trust damage and loss of work.

### Root Cause
External platform/editor issue, not CAOS app logic.

### Current Mitigation
Use external drafting for critical long messages until the platform issue is resolved.

### Prevention / Next Fix
Escalate through platform support and preserve job context/screenshots for reproduction.

---

## TSB-009 — Top Bar Duplication Creates Visual Noise
Date: 2026-04-18
Status: Active Design Correction

### Symptom
Top bar duplicated controls already present in the left rail.

### Impact
Interface felt busy and less CAOS-like.

### Root Cause
Feature-porting happened faster than layout convergence.

### Fix
Move thread-start responsibility to the left rail, simplify the header, and reduce redundant controls.

### Prevention
When porting features from old surfaces, re-evaluate hierarchy instead of preserving every control location.

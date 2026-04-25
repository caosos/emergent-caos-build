"""Autonomous memory extractor (Phase 2 of the Memory Scaffolding Blueprint).

After every chat turn, this service silently asks a cheap, fast LLM
(Gemini 3 Flash by default — $0.075 / $0.30 per 1M tokens) to inspect the
last user/assistant exchange and propose new memory atoms classified into
one of the 13 typed bins.

Design points:
  - Fire-and-forget. The chat turn returns to the user immediately; this
    runs as `asyncio.create_task` so it never blocks the reply.
  - Cheap. Gemini 3 Flash over Sonnet keeps per-turn cost in the fractions
    of a cent.
  - Conservative. We send the existing atom summaries (last 40) so the
    extractor can dedupe before proposing. We hard-cap to 5 new atoms per
    turn so a chatty model can't flood the memory.
  - Non-fatal on failure. If the LLM call errors, we swallow it and log;
    the chat turn already succeeded.

Output schema the extractor must emit (JSON):
{
  "atoms": [
    {
      "content": "User is the founder of CAOS",
      "bin": "IDENTITY_FACT",
      "summary": "Founder of CAOS",
      "confidence": 0.85,
      "evidence_quote": "I'm the founder of CAOS"
    }, ...
  ]
}
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import uuid

from emergentintegrations.llm.chat import LlmChat, UserMessage

from app.schemas.memory import BIN_REGISTRY, MemoryBin
from app.services.profile_memory_service import insert_extracted_atom, list_memory_atoms


# Cheap-fast model used for extraction. Override via env.
EXTRACTOR_PROVIDER = os.environ.get("MEMORY_EXTRACTOR_PROVIDER", "gemini")
EXTRACTOR_MODEL = os.environ.get("MEMORY_EXTRACTOR_MODEL", "gemini-3-flash-preview")
EXTRACTOR_MAX_ATOMS_PER_TURN = 5
EXTRACTOR_DEDUPE_SAMPLE = 40  # last N atoms shown to the model for dedupe


def _bin_taxonomy_block() -> str:
    """Render the 13-bin taxonomy + governance hints for the extractor prompt."""
    lines = []
    for bin_id, info in BIN_REGISTRY.items():
        if bin_id == MemoryBin.GENERAL.value:
            continue  # extractor must classify; never use GENERAL
        lines.append(f"- {bin_id}: {info['description']}")
    return "\n".join(lines)


def _extractor_system_prompt(existing_summaries: list[str]) -> str:
    sample = "\n".join(f"  - {s}" for s in existing_summaries[:EXTRACTOR_DEDUPE_SAMPLE]) or "  (none yet)"
    return f"""You are the CAOS Memory Extractor — a silent background agent that watches each chat turn and proposes new long-term memory atoms about the user.

Your output is consumed by a typed memory store with 13 governance bins:

{_bin_taxonomy_block()}

RULES:
1. Only propose atoms that contain DURABLE information about THIS USER (their identity, projects, preferences, governance rules they want, observed behavior, technical state, real-world context, learning style, relationship with AI, risk signals, counterevidence).
2. Do NOT extract chit-chat, ephemeral context, or generic statements.
3. Do NOT extract anything from the assistant's reply unless the assistant is restating something the user said.
4. SKIP if the new atom is already covered by these existing atoms:
{sample}
5. Hard-cap your output to {EXTRACTOR_MAX_ATOMS_PER_TURN} or fewer atoms.
6. Each atom MUST classify into one of the 13 typed bins above (NEVER use GENERAL).
7. Confidence is your honest estimate (0.0–1.0) of how durable/correct this is. User-stated facts → 0.85+. Patterns observed across multiple turns → 0.6–0.8. Single-turn inferences → 0.3–0.5.
8. evidence_quote should be a direct quote (≤200 chars) from the user message that supports the atom.

OUTPUT: ONLY a JSON object, no preamble, no markdown fence:
{{"atoms": [{{"content": "...", "bin": "IDENTITY_FACT", "summary": "...", "confidence": 0.0, "evidence_quote": "..."}}]}}

If nothing worth saving, output: {{"atoms": []}}"""


_VALID_BINS = {b.value for b in MemoryBin if b != MemoryBin.GENERAL}


def _parse_extractor_json(reply: str) -> list[dict]:
    """Parse the extractor's JSON reply, robust to markdown fences / chatter."""
    if not reply:
        return []
    text = reply.strip()
    # Strip ```json fences if the model wraps despite instructions
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    # If still wrapped in prose, extract the first {...} block
    if not text.startswith("{"):
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            text = match.group(0)
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return []
    atoms = data.get("atoms") if isinstance(data, dict) else None
    if not isinstance(atoms, list):
        return []
    out = []
    for raw in atoms[:EXTRACTOR_MAX_ATOMS_PER_TURN]:
        if not isinstance(raw, dict):
            continue
        content = (raw.get("content") or "").strip()
        bin_name = (raw.get("bin") or "").strip().upper()
        if not content or len(content) < 8:
            continue
        if bin_name not in _VALID_BINS:
            continue
        out.append({
            "content": content[:600],
            "bin": bin_name,
            "summary": (raw.get("summary") or content)[:200],
            "confidence": float(raw.get("confidence") or 0.5),
            "evidence_quote": (raw.get("evidence_quote") or content)[:300],
        })
    return out


async def extract_memories_from_turn(
    *,
    user_email: str,
    session_id: str,
    user_message: str,
    assistant_reply: str,
    user_message_id: str | None = None,
) -> list[str]:
    """Run the extractor and persist any new atoms. Returns list of atom IDs created.

    Designed to be called via `asyncio.create_task(...)` from chat_pipeline so
    it never blocks the user's reply. All errors are swallowed (and printed).
    """
    try:
        api_key = os.environ.get("EMERGENT_LLM_KEY")
        if not api_key:
            return []
        existing = await list_memory_atoms(user_email)
        existing_summaries = [
            f"[{a.bin_name}] {a.summary or a.content[:120]}"
            for a in existing[:EXTRACTOR_DEDUPE_SAMPLE]
        ]
        system_prompt = _extractor_system_prompt(existing_summaries)
        chat = LlmChat(
            api_key=api_key,
            session_id=f"memextract-{uuid.uuid4().hex[:12]}",
            system_message=system_prompt,
        ).with_model(EXTRACTOR_PROVIDER, EXTRACTOR_MODEL)
        # Single-turn extraction: pass the user's message + assistant reply as
        # the "exchange to inspect".
        prompt = (
            f"USER MESSAGE:\n{user_message[:3000]}\n\n"
            f"ASSISTANT REPLY:\n{assistant_reply[:1500]}\n\n"
            "Extract memory atoms per the rules. JSON only."
        )
        reply = await chat.send_message(UserMessage(text=prompt))
        proposals = _parse_extractor_json(reply)
        created_ids: list[str] = []
        for atom_proposal in proposals:
            atom = await insert_extracted_atom(
                user_email,
                content=atom_proposal["content"],
                bin_name=atom_proposal["bin"],
                summary=atom_proposal["summary"],
                source_session_id=session_id,
                source_message_id=user_message_id or session_id,
                confidence=atom_proposal["confidence"],
                evidence_quote=atom_proposal["evidence_quote"],
                evidence_strength=atom_proposal["confidence"],
            )
            if atom is not None:
                created_ids.append(atom.id)
        if created_ids:
            print(f"CAOS memory extractor: +{len(created_ids)} atoms for {user_email}")
        return created_ids
    except Exception as exc:  # pragma: no cover — non-fatal
        print(f"CAOS memory extractor failed for {user_email}: {exc}")
        return []


def schedule_extraction(
    *,
    user_email: str,
    session_id: str,
    user_message: str,
    assistant_reply: str,
    user_message_id: str | None = None,
) -> asyncio.Task:
    """Fire-and-forget wrapper. Returns the created Task so callers may
    optionally await/inspect it; chat_pipeline does not await it."""
    return asyncio.create_task(
        extract_memories_from_turn(
            user_email=user_email,
            session_id=session_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
            user_message_id=user_message_id,
        )
    )

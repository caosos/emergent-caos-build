"""Multi-agent parallel fan-out service.

Fires the same user prompt at multiple providers concurrently and returns each
response as its own slot. The chat pipeline is reused for every fan-out so
memory/continuity/receipts still apply — we just run N of them in parallel.

Adds a Synthesizer step: once the fan-out completes, a 4th LLM call
(Claude Sonnet 4.5 by default) reads all successful agent replies and produces
a single consolidated answer with inline [Claude] / [GPT] / [Gemini] citations.
"""
from __future__ import annotations

import asyncio
import os
import uuid
from dataclasses import dataclass

from emergentintegrations.llm.chat import LlmChat, UserMessage

from app.schemas.caos import ChatRequest, ChatResponse
from app.services.chat_pipeline import run_chat_turn


@dataclass
class AgentPick:
    provider: str
    model: str
    label: str


DEFAULT_MULTI_AGENT_PANEL: list[AgentPick] = [
    AgentPick(provider="anthropic", model="claude-sonnet-4-5-20250929", label="Claude"),
    AgentPick(provider="openai", model="gpt-5.2", label="OpenAI"),
    AgentPick(provider="gemini", model="gemini-3-flash-preview", label="Gemini"),
]

SYNTHESIZER_PROVIDER = "anthropic"
SYNTHESIZER_MODEL = "claude-sonnet-4-5-20250929"
SYNTHESIZER_SYSTEM = """You are the Synthesizer for CAOS's Multi-Agent mode.

Three independent assistants (Claude, OpenAI, and Gemini) have answered the same user prompt in parallel. Your job is to produce ONE consolidated, best-of-all-worlds reply that the user will read FIRST, before (optionally) inspecting the raw column outputs.

Rules:
1. Read all three replies carefully. Identify agreement, disagreement, unique insights, and factual claims.
2. Write ONE concise, cohesive answer in your own words — do NOT just list three bullet points.
3. When a specific fact/insight/example comes primarily from one agent, append a lightweight inline citation: [Claude], [GPT], or [Gemini]. Use [All] when all three agree.
4. If the agents disagree on a factual point, acknowledge it briefly: "Claude and GPT say X [Claude][GPT], while Gemini says Y [Gemini]."
5. If one agent clearly failed or gave a low-quality answer, silently omit it — do not mention failures.
6. Prefer clarity and brevity. No preamble ("Here is a synthesis..."), no headers, no bullet list unless the original prompt asked for one.
7. Match the tone the user seems to want (technical, casual, etc.).

Output ONLY the synthesized answer text."""


async def _run_one_agent(base: ChatRequest, pick: AgentPick) -> dict:
    try:
        response: ChatResponse = await run_chat_turn(
            ChatRequest(
                user_email=base.user_email,
                session_id=base.session_id,
                content=base.content,
                provider=pick.provider,
                model=pick.model,
                hot_head=base.hot_head,
                hot_tail=base.hot_tail,
                memory_limit=base.memory_limit,
                history_token_budget=base.history_token_budget,
            )
        )
        return {
            "provider": pick.provider,
            "model": pick.model,
            "label": pick.label,
            "ok": True,
            "reply": response.reply,
            "wcw_used_estimate": response.wcw_used_estimate,
            "wcw_budget": response.wcw_budget,
            "assistant_message_id": response.assistant_message.id,
        }
    except Exception as error:
        return {
            "provider": pick.provider,
            "model": pick.model,
            "label": pick.label,
            "ok": False,
            "error": str(error)[:240],
        }


def _format_agent_column(result: dict) -> str:
    return f"--- [{result['label']} · {result['model']}] ---\n{result['reply']}"


async def run_synthesizer(prompt: str, successful_agents: list[dict]) -> dict:
    """Run the 4th LLM call — read 3 parallel replies, produce one consolidated answer."""
    if len(successful_agents) < 2:
        # Synthesis needs at least 2 agents to be meaningful. Skip silently otherwise.
        return {"ok": False, "skipped": True, "reason": "fewer_than_two_agents"}
    try:
        panel = "\n\n".join(_format_agent_column(item) for item in successful_agents)
        synth_input = (
            f"User prompt:\n{prompt}\n\n"
            f"Agent replies to merge:\n{panel}\n\n"
            "Write the synthesized answer now."
        )
        chat = LlmChat(
            api_key=os.environ["EMERGENT_LLM_KEY"],
            session_id=f"synthesizer-{uuid.uuid4()}",
            system_message=SYNTHESIZER_SYSTEM,
        ).with_model(SYNTHESIZER_PROVIDER, SYNTHESIZER_MODEL)
        pending = await chat.get_messages()
        await chat._add_user_message(pending, UserMessage(text=synth_input))
        completion = await chat._execute_completion(pending)
        text = await chat._extract_response_text(completion)
        return {
            "ok": True,
            "provider": SYNTHESIZER_PROVIDER,
            "model": SYNTHESIZER_MODEL,
            "label": "Synthesizer",
            "reply": text,
            "source_labels": [a["label"] for a in successful_agents],
        }
    except Exception as error:
        return {"ok": False, "error": str(error)[:240]}


async def run_multi_agent_turn(base: ChatRequest, picks: list[AgentPick] | None = None) -> dict:
    panel = picks or DEFAULT_MULTI_AGENT_PANEL
    results = await asyncio.gather(*[_run_one_agent(base, pick) for pick in panel])
    successful = [item for item in results if item.get("ok")]
    synthesis = await run_synthesizer(base.content, successful)
    return {
        "session_id": base.session_id,
        "prompt": base.content,
        "agents": results,
        "synthesis": synthesis,
        "ok_count": len(successful),
        "fail_count": sum(1 for result in results if not result.get("ok")),
    }

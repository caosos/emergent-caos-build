"""Multi-agent parallel fan-out service.

Fires the same user prompt at multiple providers concurrently and returns each
response as its own slot. The chat pipeline is reused for every fan-out so
memory/continuity/receipts still apply — we just run N of them in parallel.
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass

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


async def run_multi_agent_turn(base: ChatRequest, picks: list[AgentPick] | None = None) -> dict:
    panel = picks or DEFAULT_MULTI_AGENT_PANEL
    results = await asyncio.gather(*[_run_one_agent(base, pick) for pick in panel])
    return {
        "session_id": base.session_id,
        "prompt": base.content,
        "agents": results,
        "ok_count": sum(1 for result in results if result.get("ok")),
        "fail_count": sum(1 for result in results if not result.get("ok")),
    }

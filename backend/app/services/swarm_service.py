"""Orchestrated Swarm v1 — Supervisor → Worker → Critic.

Flow:
1. Supervisor (Claude Sonnet 4.5) reads the user task and produces a JSON plan:
   {"objective": str, "steps": [{"id": str, "description": str, "python": str}]}
2. Workers run each step's Python snippet in an E2B Cloud Sandbox.
3. Critic (Claude Sonnet 4.5) reviews objective + step outputs and produces a
   final answer (with any corrections, caveats, and a clear summary).

Each stage is streamed back to the client via SSE events so the UI can show
live progress ("Planning…", "Step 2/3 running…", "Critic reviewing…", "Done").
"""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import dataclass

from e2b_code_interpreter import Sandbox
from emergentintegrations.llm.chat import LlmChat, UserMessage

from app.services.swarm_tools import run_tool, TOOL_DOCS


SUPERVISOR_MODEL = "claude-sonnet-4-5-20250929"
CRITIC_MODEL = "claude-sonnet-4-5-20250929"
SUPERVISOR_PROVIDER = "anthropic"
CRITIC_PROVIDER = "anthropic"

SUPERVISOR_SYSTEM = f"""You are the Supervisor for CAOS's Agent Swarm.

Given a user task, produce a JSON plan with 1 to 6 steps. Each step is either:
  - a SERVER-SIDE TOOL CALL (type="tool") — reads the CAOS repo live at /app
  - a SANDBOX PYTHON SNIPPET (type="python") — runs in an isolated E2B Cloud Sandbox

{TOOL_DOCS}

Python steps run in an E2B sandbox with stdlib + numpy + pandas + requests. Sandbox has NO repo access — use tools for file/grep work, python for computation/data-crunching.

Rules:
- Output ONLY valid JSON — no prose, no markdown code fences.
- Top-level shape: {{"objective": string, "steps": [step, ...]}}
- Each step has: {{"id": "s1", "type": "tool"|"python", "description": "..."}}
  - If type="tool": add `"tool_name": "...", "tool_args": {{...}}`
  - If type="python": add `"python": "..."` (valid Python 3; use print() for outputs)
- Keep each step small. Chain tool calls before python when you need file contents to analyse.
- If the task is purely conversational, return {{"objective": "...", "steps": []}} — the Critic will answer directly.

Example — user asks "What does the chat_pipeline.py file do?":
{{"objective":"Read chat_pipeline.py and summarise it","steps":[
  {{"id":"s1","type":"tool","description":"Read the chat pipeline source","tool_name":"caos_read_file","tool_args":{{"path":"backend/app/services/chat_pipeline.py"}}}}
]}}

Example — user asks "Grep for every function named sendMessage":
{{"objective":"Find all sendMessage definitions","steps":[
  {{"id":"s1","type":"tool","description":"Grep for sendMessage definitions","tool_name":"caos_grep","tool_args":{{"pattern":"(def |const |function )sendMessage","path":"."}}}}
]}}

Example — user asks "Add 1+1":
{{"objective":"Compute 1+1","steps":[
  {{"id":"s1","type":"python","description":"Print 1+1","python":"print(1+1)"}}
]}}"""

CRITIC_SYSTEM = """You are the Critic for CAOS's Agent Swarm.

You are given:
1. The user's original task
2. The Supervisor's plan
3. The stdout/stderr output from each step the Worker executed in a sandbox

Write a clear, direct final answer to the user. Use the worker outputs as ground truth. If outputs have errors or are missing, say so briefly and give the best possible answer from available info. Be concise. No preamble. Match the tone the user seems to want."""


@dataclass
class SwarmStep:
    id: str
    description: str
    type: str = "python"
    python: str = ""
    tool_name: str = ""
    tool_args: dict | None = None
    stdout: str = ""
    stderr: str = ""
    error: str = ""


async def _call_llm(provider: str, model: str, system: str, user_text: str) -> str:
    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"swarm-{uuid.uuid4()}",
        system_message=system,
    ).with_model(provider, model)
    pending = await chat.get_messages()
    await chat._add_user_message(pending, UserMessage(text=user_text))
    completion = await chat._execute_completion(pending)
    return await chat._extract_response_text(completion)


def _safe_json_extract(raw: str) -> dict:
    """LLMs sometimes wrap JSON in fences despite instructions. Strip and parse."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(line for line in lines if not line.startswith("```"))
    return json.loads(text)


async def run_supervisor(task: str) -> dict:
    raw = await _call_llm(SUPERVISOR_PROVIDER, SUPERVISOR_MODEL, SUPERVISOR_SYSTEM, task)
    try:
        plan = _safe_json_extract(raw)
    except json.JSONDecodeError as error:
        raise ValueError(f"Supervisor returned invalid JSON: {error}") from error
    if "objective" not in plan or "steps" not in plan:
        raise ValueError("Supervisor plan missing required fields")
    return plan


def _run_step_in_sandbox(sandbox: Sandbox, python: str) -> dict:
    try:
        execution = sandbox.run_code(python, timeout=45)
        stdout = "".join(getattr(execution.logs, "stdout", []) or [])
        stderr = "".join(getattr(execution.logs, "stderr", []) or [])
        err = execution.error
        return {
            "stdout": stdout,
            "stderr": stderr,
            "error": str(err) if err else "",
        }
    except Exception as error:
        return {"stdout": "", "stderr": "", "error": str(error)[:400]}


async def run_workers(steps: list[dict]) -> list[SwarmStep]:
    """Dispatch each step: type="tool" runs server-side in this process, type="python"
    runs in a shared E2B sandbox (state preserved across python steps)."""
    results: list[SwarmStep] = []
    api_key = os.environ.get("E2B_API_KEY")
    sandbox: Sandbox | None = None

    def ensure_sandbox() -> Sandbox | None:
        nonlocal sandbox
        if sandbox is not None:
            return sandbox
        if not api_key:
            return None
        sandbox = Sandbox.create(api_key=api_key, timeout=120)
        return sandbox

    try:
        for step in steps:
            step_type = step.get("type", "python")
            base_fields = {
                "id": step.get("id", "s?"),
                "description": step.get("description", ""),
                "type": step_type,
                "python": step.get("python", ""),
                "tool_name": step.get("tool_name", ""),
                "tool_args": step.get("tool_args") or {},
            }
            if step_type == "tool":
                outcome = run_tool(step.get("tool_name", ""), step.get("tool_args") or {})
            else:
                sb = ensure_sandbox()
                if sb is None:
                    outcome = {"stdout": "", "stderr": "", "error": "E2B_API_KEY not configured"}
                else:
                    outcome = _run_step_in_sandbox(sb, step.get("python", ""))
            results.append(SwarmStep(
                **base_fields,
                stdout=outcome["stdout"][:6000],
                stderr=outcome["stderr"][:2000],
                error=outcome["error"][:400],
            ))
    finally:
        if sandbox is not None:
            try:
                sandbox.kill()
            except Exception:
                pass
    return results


async def run_critic(task: str, plan: dict, executed_steps: list[SwarmStep]) -> str:
    step_dump = "\n\n".join(
        f"[{step.id}] {step.description}\nstdout:\n{step.stdout or '(empty)'}"
        + (f"\nstderr:\n{step.stderr}" if step.stderr else "")
        + (f"\nERROR: {step.error}" if step.error else "")
        for step in executed_steps
    ) or "(no steps were executed — answer directly from task)"
    prompt = (
        f"User task:\n{task}\n\n"
        f"Supervisor's objective: {plan.get('objective', '(none)')}\n\n"
        f"Worker outputs:\n{step_dump}\n\n"
        "Write the final answer for the user now."
    )
    return await _call_llm(CRITIC_PROVIDER, CRITIC_MODEL, CRITIC_SYSTEM, prompt)


async def run_swarm(task: str) -> dict:
    """Non-streaming convenience wrapper — returns everything at once."""
    plan = await run_supervisor(task)
    executed = await run_workers(plan.get("steps", []))
    final = await run_critic(task, plan, executed)
    return {
        "task": task,
        "plan": plan,
        "steps": [step.__dict__ for step in executed],
        "final_answer": final,
    }

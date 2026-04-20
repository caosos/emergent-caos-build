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


SUPERVISOR_MODEL = "claude-sonnet-4-5-20250929"
CRITIC_MODEL = "claude-sonnet-4-5-20250929"
SUPERVISOR_PROVIDER = "anthropic"
CRITIC_PROVIDER = "anthropic"

SUPERVISOR_SYSTEM = """You are the Supervisor for CAOS's Agent Swarm.

Given a user task, produce a JSON plan with 1 to 4 steps. Each step must be a small, self-contained piece of Python code that a worker will run in a sandboxed environment (stdout is captured and returned to the Critic).

Rules:
- Output ONLY valid JSON — no prose, no markdown code fences.
- Shape: {"objective": string, "steps": [{"id": "s1", "description": "…", "python": "…"}, …]}
- Each `python` is executable Python 3 code that prints useful output.
- Prefer `print(…)` for results so the Critic can see them.
- Keep each step small (under ~40 lines).
- If the task is conversational and doesn't need code execution, return {"objective": "…", "steps": []} and the Critic will answer directly.
- Available libraries in sandbox: standard library + numpy, pandas, requests. Do NOT assume internet access (it's limited).

Example input: "What are the first 10 prime numbers and their sum?"
Example output: {"objective":"List first 10 primes and their sum","steps":[{"id":"s1","description":"Generate primes","python":"def is_prime(n):\\n    if n<2: return False\\n    for i in range(2,int(n**0.5)+1):\\n        if n%i==0: return False\\n    return True\\nprimes=[]\\nn=2\\nwhile len(primes)<10:\\n    if is_prime(n): primes.append(n)\\n    n+=1\\nprint('primes:',primes)\\nprint('sum:',sum(primes))"}]}"""

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
    python: str
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
    """Spin up a single E2B sandbox and run all steps sequentially in it so state
    (variables, installed modules) is preserved across steps."""
    results: list[SwarmStep] = []
    api_key = os.environ.get("E2B_API_KEY")
    if not api_key:
        for step in steps:
            results.append(SwarmStep(
                id=step.get("id", "s?"),
                description=step.get("description", ""),
                python=step.get("python", ""),
                error="E2B_API_KEY not configured",
            ))
        return results
    sandbox = Sandbox.create(api_key=api_key, timeout=120)
    try:
        for step in steps:
            outcome = _run_step_in_sandbox(sandbox, step.get("python", ""))
            results.append(SwarmStep(
                id=step.get("id", "s?"),
                description=step.get("description", ""),
                python=step.get("python", ""),
                stdout=outcome["stdout"][:4000],
                stderr=outcome["stderr"][:2000],
                error=outcome["error"][:400],
            ))
    finally:
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

"""Swarm server-side tools.

These run in the backend process (not in the E2B sandbox) because they need
read access to the actual CAOS repo at /app. The Supervisor can call them as
step type="tool" to grep code, read files, list directories, or check recent
git commits.

Every tool is READ-ONLY. No writes to the repo, no shell-outs outside the
/app root, no network. Outputs are capped to keep prompt budget sane.
"""
from __future__ import annotations

import subprocess
from pathlib import Path


REPO_ROOT = Path("/app")
MAX_OUTPUT_CHARS = 6000


def _safe_path(relative: str) -> Path:
    """Resolve `relative` inside REPO_ROOT and reject escapes."""
    target = (REPO_ROOT / relative.lstrip("/")).resolve()
    if not str(target).startswith(str(REPO_ROOT)):
        raise ValueError(f"path '{relative}' escapes repo root")
    return target


def _clip(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + f"\n... [truncated {len(text) - MAX_OUTPUT_CHARS} chars]"


def caos_grep(pattern: str, path: str = ".", file_glob: str | None = None) -> str:
    """Recursive grep across the repo. Returns matched lines with file:line prefixes."""
    target = _safe_path(path)
    if not target.exists():
        return f"(no such path: {path})"
    cmd = ["grep", "-rn", "--color=never", "-E", pattern, str(target)]
    if file_glob:
        cmd.extend(["--include", file_glob])
    # Sensible excludes so we don't return megabytes of lockfiles / build artifacts.
    for skip in ("node_modules", ".git", "__pycache__", "dist", "build", ".next", ".venv"):
        cmd.extend(["--exclude-dir", skip])
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        out = result.stdout or "(no matches)"
        return _clip(out)
    except subprocess.TimeoutExpired:
        return "(grep timed out after 15s)"
    except Exception as error:
        return f"(grep failed: {error})"


def caos_read_file(path: str, start_line: int = 1, end_line: int | None = None) -> str:
    """Read a file from the repo. Line-range is 1-indexed and inclusive."""
    target = _safe_path(path)
    if not target.exists() or not target.is_file():
        return f"(no such file: {path})"
    try:
        lines = target.read_text(errors="replace").splitlines()
    except Exception as error:
        return f"(read failed: {error})"
    total = len(lines)
    start = max(1, start_line) - 1
    end = min(total, end_line) if end_line else total
    selected = lines[start:end]
    numbered = "\n".join(f"{i+1+start}: {line}" for i, line in enumerate(selected))
    header = f"# {path}  (showing lines {start+1}-{start+len(selected)} of {total})\n"
    return _clip(header + numbered)


def caos_ls(path: str = ".", max_depth: int = 1) -> str:
    """List directory contents up to a given depth. Hides hidden and noise dirs."""
    target = _safe_path(path)
    if not target.exists() or not target.is_dir():
        return f"(no such directory: {path})"
    noise = {"node_modules", ".git", "__pycache__", "dist", "build", ".next", ".venv"}
    lines: list[str] = []

    def walk(current: Path, depth: int) -> None:
        if depth > max_depth:
            return
        try:
            entries = sorted(current.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower()))
        except PermissionError:
            return
        for entry in entries:
            if entry.name.startswith(".") or entry.name in noise:
                continue
            rel = entry.relative_to(REPO_ROOT)
            suffix = "/" if entry.is_dir() else ""
            lines.append(f"{'  ' * (depth - 1)}{entry.name}{suffix}")
            if entry.is_dir():
                walk(entry, depth + 1)

    walk(target, 1)
    if not lines:
        return "(empty)"
    return _clip(f"# {path}\n" + "\n".join(lines))


def caos_git_log(limit: int = 10) -> str:
    """Return the most recent git commits on the current branch."""
    try:
        result = subprocess.run(
            ["git", "log", f"-n{int(limit)}", "--pretty=format:%h  %ad  %s", "--date=short"],
            capture_output=True, text=True, timeout=10, cwd=str(REPO_ROOT),
        )
        return _clip(result.stdout or "(no commits)")
    except Exception as error:
        return f"(git log failed: {error})"


TOOL_REGISTRY = {
    "caos_grep": caos_grep,
    "caos_read_file": caos_read_file,
    "caos_ls": caos_ls,
    "caos_git_log": caos_git_log,
}


def run_tool(tool_name: str, tool_args: dict) -> dict:
    """Dispatch a tool call by name. Returns {stdout, stderr, error}."""
    fn = TOOL_REGISTRY.get(tool_name)
    if not fn:
        return {"stdout": "", "stderr": "", "error": f"unknown tool: {tool_name}"}
    try:
        output = fn(**(tool_args or {}))
        return {"stdout": str(output), "stderr": "", "error": ""}
    except TypeError as error:
        return {"stdout": "", "stderr": "", "error": f"bad args for {tool_name}: {error}"}
    except Exception as error:
        return {"stdout": "", "stderr": "", "error": f"{tool_name} raised: {str(error)[:240]}"}


TOOL_DOCS = """Available server-side tools (step type="tool", provide `tool_name` and `tool_args` dict):
- caos_grep(pattern, path=".", file_glob=None)         → grep -rnE across the CAOS repo at /app. file_glob is an optional --include pattern like "*.py".
- caos_read_file(path, start_line=1, end_line=None)    → read a file, optionally a line range. Paths are repo-relative.
- caos_ls(path=".", max_depth=1)                       → list directory contents (hides node_modules/.git/__pycache__).
- caos_git_log(limit=10)                               → last N git commits (short-hash  date  subject).

These tools run in the CAOS backend itself — they CAN see the live CAOS source code at /app. Prefer tools over python for anything that touches repo files."""

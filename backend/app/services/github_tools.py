"""GitHub adapter for the Swarm.

Read-only tools that hit the GitHub REST API. Uses a personal access token
from `GITHUB_TOKEN` in the backend env — without it, each call returns a
clear "configure GITHUB_TOKEN" message so nothing crashes.

Permissions needed on the PAT:
  - `repo` (for private repos) or just `public_repo` (public only)
  - `read:user`, `read:org` (optional — for whoami / org listings)

Everything here is READ-ONLY by design:
  - gh_whoami()                            → auth sanity check
  - gh_list_repos(visibility, limit)       → your repos
  - gh_read_file(repo, path, ref)          → file contents from any branch
  - gh_list_prs(repo, state, limit)        → PRs with title/number/state/author
  - gh_read_pr(repo, number)               → PR metadata + body + changed files
  - gh_list_issues(repo, state, limit)     → open issues
  - gh_search_code(repo, query, limit)     → GitHub code search within a repo
  - gh_file_history(repo, path, limit)     → commits touching a file
"""
from __future__ import annotations

import base64
import os

import httpx


API_BASE = "https://api.github.com"
USER_AGENT = "CAOS-Swarm/1.0"
MAX_OUTPUT_CHARS = 8000


def _clip(text: str) -> str:
    if len(text) <= MAX_OUTPUT_CHARS:
        return text
    return text[:MAX_OUTPUT_CHARS] + f"\n... [truncated {len(text) - MAX_OUTPUT_CHARS} chars]"


def _headers() -> dict[str, str] | None:
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": USER_AGENT,
    }


def _get(path: str, params: dict | None = None) -> str | dict | list:
    headers = _headers()
    if headers is None:
        return "(GITHUB_TOKEN not configured — please set it in /app/backend/.env and restart backend)"
    try:
        response = httpx.get(f"{API_BASE}{path}", headers=headers, params=params or {}, timeout=15)
    except Exception as error:
        return f"(GitHub request failed: {error})"
    if response.status_code >= 400:
        return f"(GitHub API {response.status_code}: {response.text[:300]})"
    try:
        return response.json()
    except Exception:
        return response.text


def gh_whoami() -> str:
    data = _get("/user")
    if isinstance(data, str):
        return data
    return _clip(f"Authenticated as {data.get('login')} ({data.get('name') or 'no name'}) · public repos: {data.get('public_repos')}")


def gh_list_repos(visibility: str = "all", limit: int = 30) -> str:
    params = {"per_page": min(int(limit), 100), "sort": "updated", "visibility": visibility}
    data = _get("/user/repos", params=params)
    if isinstance(data, str):
        return data
    rows = [f"{r.get('full_name')}  ({'private' if r.get('private') else 'public'})  · updated {r.get('updated_at')}  · {r.get('description') or 'no description'}" for r in data]
    return _clip("\n".join(rows) or "(no repos)")


def gh_read_file(repo: str, path: str, ref: str = "main") -> str:
    data = _get(f"/repos/{repo}/contents/{path.lstrip('/')}", params={"ref": ref})
    if isinstance(data, str):
        return data
    if isinstance(data, list):
        return _clip(f"# {repo}:{path} is a directory.\n" + "\n".join(f"- {item.get('name')}  ({item.get('type')})" for item in data))
    content = data.get("content", "")
    encoding = data.get("encoding", "base64")
    if encoding == "base64":
        try:
            decoded = base64.b64decode(content).decode("utf-8", errors="replace")
        except Exception as error:
            return f"(decode failed: {error})"
    else:
        decoded = str(content)
    header = f"# {repo}:{path}@{ref}  ({data.get('size')} bytes)\n"
    return _clip(header + decoded)


def gh_list_prs(repo: str, state: str = "open", limit: int = 20) -> str:
    params = {"state": state, "per_page": min(int(limit), 100), "sort": "updated", "direction": "desc"}
    data = _get(f"/repos/{repo}/pulls", params=params)
    if isinstance(data, str):
        return data
    rows = [f"#{pr.get('number')}  [{pr.get('state')}]  {pr.get('title')}  · {pr.get('user',{}).get('login')} · {pr.get('updated_at')}" for pr in data]
    return _clip("\n".join(rows) or f"(no {state} PRs)")


def gh_read_pr(repo: str, number: int) -> str:
    pr = _get(f"/repos/{repo}/pulls/{number}")
    if isinstance(pr, str):
        return pr
    files = _get(f"/repos/{repo}/pulls/{number}/files", params={"per_page": 50})
    file_lines = []
    if isinstance(files, list):
        for f in files:
            file_lines.append(f"  {f.get('status')}  {f.get('filename')}  (+{f.get('additions')} -{f.get('deletions')})")
    body = pr.get("body") or "(no body)"
    header = (
        f"PR #{pr.get('number')} [{pr.get('state')}]  {pr.get('title')}\n"
        f"by {pr.get('user',{}).get('login')} · {pr.get('head',{}).get('ref')} → {pr.get('base',{}).get('ref')}\n"
        f"Merged: {pr.get('merged')}  · Comments: {pr.get('comments')}\n\n"
        f"Body:\n{body}\n\n"
        f"Files:\n" + "\n".join(file_lines)
    )
    return _clip(header)


def gh_list_issues(repo: str, state: str = "open", limit: int = 20) -> str:
    params = {"state": state, "per_page": min(int(limit), 100), "sort": "updated", "direction": "desc"}
    data = _get(f"/repos/{repo}/issues", params=params)
    if isinstance(data, str):
        return data
    rows = []
    for issue in data:
        if issue.get("pull_request"):
            continue  # /issues also returns PRs; skip them
        labels = ",".join(lbl.get("name", "") for lbl in issue.get("labels", []))
        rows.append(f"#{issue.get('number')}  [{issue.get('state')}]  {issue.get('title')}  · labels: {labels or '-'}  · {issue.get('updated_at')}")
    return _clip("\n".join(rows) or f"(no {state} issues)")


def gh_search_code(repo: str, query: str, limit: int = 15) -> str:
    params = {"q": f"{query} repo:{repo}", "per_page": min(int(limit), 50)}
    data = _get("/search/code", params=params)
    if isinstance(data, str):
        return data
    items = data.get("items", []) if isinstance(data, dict) else []
    rows = [f"{item.get('path')}  ·  {item.get('repository', {}).get('full_name')}" for item in items]
    return _clip(f"Total matches: {data.get('total_count', 0) if isinstance(data, dict) else '?'}\n" + "\n".join(rows) or "(no matches)")


def gh_file_history(repo: str, path: str, limit: int = 10) -> str:
    params = {"path": path, "per_page": min(int(limit), 50)}
    data = _get(f"/repos/{repo}/commits", params=params)
    if isinstance(data, str):
        return data
    rows = []
    for commit in data:
        meta = commit.get("commit", {})
        author = meta.get("author", {})
        msg_first_line = (meta.get("message") or "").splitlines()[0] if meta.get("message") else ""
        rows.append(f"{commit.get('sha','')[:8]}  {author.get('date','')}  {author.get('name','')}  · {msg_first_line}")
    return _clip("\n".join(rows) or f"(no commits touching {path})")


GITHUB_TOOL_REGISTRY = {
    "gh_whoami": gh_whoami,
    "gh_list_repos": gh_list_repos,
    "gh_read_file": gh_read_file,
    "gh_list_prs": gh_list_prs,
    "gh_read_pr": gh_read_pr,
    "gh_list_issues": gh_list_issues,
    "gh_search_code": gh_search_code,
    "gh_file_history": gh_file_history,
}


GITHUB_TOOL_DOCS = """GitHub read-only tools (require GITHUB_TOKEN in backend env):
- gh_whoami()                                          → confirm auth works.
- gh_list_repos(visibility="all", limit=30)            → your repos (most recently updated first). visibility ∈ {all, public, private}.
- gh_read_file(repo, path, ref="main")                 → file contents from any branch/tag. `repo` is "owner/name".
- gh_list_prs(repo, state="open", limit=20)            → PRs. state ∈ {open, closed, all}.
- gh_read_pr(repo, number)                             → PR metadata + body + changed files list.
- gh_list_issues(repo, state="open", limit=20)         → issues (PRs filtered out).
- gh_search_code(repo, query, limit=15)                → GitHub code search within a specific repo.
- gh_file_history(repo, path, limit=10)                → commits touching a file."""

"""Minimal MCP (Model Context Protocol) client over JSON-RPC HTTP.

CAOS as MCP HOST
================
Each user can register N MCP servers in the Connectors hub. We:

1. Cache every server's `tools/list` schema locally (refreshed on demand).
2. At chat time, inject every connected server's tool catalog into Aria's
   system prompt as `[MCP TOOL: <server_id>:<tool_name> ...]` markers.
3. When Aria emits an `[MCP_CALL: <server_id>:<tool_name> {...}]` marker,
   we route the JSON args via JSON-RPC `tools/call` to the server, return
   the rendered text result.

The full MCP spec covers stdio, websocket, SSE transports + resources,
prompts, sampling, etc. For Sprint 2 we ship the smallest useful subset:

  - HTTP POST transport (most public MCP servers expose this)
  - tools/list + tools/call only
  - Per-server static auth header (e.g. "Authorization: Bearer ...")

Adding stdio / SSE / resources is straightforward later — every method below
takes the server URL as the only stateful input.

Storage
-------
collection `mcp_servers`:
  user_email     str
  server_id      str (uuid generated on insert)
  name           str — display label
  url            str — JSON-RPC HTTP endpoint
  auth_header    str | None — sent as Authorization: <value>
  tools_cache    [ {name, description, input_schema} ]
  enabled        bool
  last_error     str | None
  created_at, updated_at
"""
from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any

import httpx

from app.db import collection

MCP_TIMEOUT_SECONDS = 25
MAX_TOOL_CONTENT_BYTES = 64 * 1024


class McpError(Exception):
    """Raised when an MCP server cannot be reached or returns an error."""


def _gen_id() -> str:
    return f"mcp_{secrets.token_hex(8)}"


def _headers(auth_header: str | None) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if auth_header:
        headers["Authorization"] = auth_header
    return headers


async def _call_jsonrpc(
    url: str, method: str, params: dict[str, Any] | None, auth_header: str | None,
) -> Any:
    """Single JSON-RPC 2.0 call. Returns the `result` field on success."""
    payload = {"jsonrpc": "2.0", "id": secrets.token_hex(4), "method": method}
    if params is not None:
        payload["params"] = params
    try:
        async with httpx.AsyncClient(timeout=MCP_TIMEOUT_SECONDS) as http:
            resp = await http.post(url, json=payload, headers=_headers(auth_header))
    except httpx.RequestError as error:
        raise McpError(f"network: {str(error)[:160]}") from error
    if resp.status_code >= 400:
        raise McpError(f"HTTP {resp.status_code}: {(resp.text or '')[:200]}")
    try:
        body = resp.json()
    except Exception as error:
        raise McpError(f"invalid JSON response: {str(error)[:120]}") from error
    if not isinstance(body, dict):
        raise McpError(f"non-object response: {str(body)[:120]}")
    if "error" in body:
        err = body["error"]
        msg = err.get("message", "?") if isinstance(err, dict) else str(err)
        raise McpError(f"server error: {msg[:200]}")
    return body.get("result")


async def list_tools(url: str, auth_header: str | None) -> list[dict[str, Any]]:
    """Hit `tools/list` and return the raw tool descriptors."""
    result = await _call_jsonrpc(url, "tools/list", {}, auth_header)
    if isinstance(result, dict):
        tools = result.get("tools") or []
    elif isinstance(result, list):
        tools = result
    else:
        tools = []
    return [
        {
            "name": t.get("name") or "?",
            "description": (t.get("description") or "")[:400],
            "input_schema": t.get("inputSchema") or t.get("input_schema") or {},
        }
        for t in tools
        if isinstance(t, dict)
    ]


async def call_tool(
    url: str, auth_header: str | None, tool_name: str, args: dict[str, Any],
) -> str:
    """Hit `tools/call` and render the result content as a string for Aria."""
    result = await _call_jsonrpc(
        url, "tools/call", {"name": tool_name, "arguments": args or {}}, auth_header,
    )
    # MCP tool results come as { content: [{type: "text", text: "..."}], ... }
    content = (result or {}).get("content") or []
    out: list[str] = []
    if isinstance(content, list):
        for piece in content:
            if not isinstance(piece, dict):
                continue
            if piece.get("type") == "text":
                out.append(str(piece.get("text") or ""))
            elif piece.get("type") == "resource":
                ref = piece.get("resource") or {}
                out.append(f"[resource: {ref.get('uri') or '?'}]")
    if not out:
        # Fallback: dump the whole result.
        out.append(str(result)[:MAX_TOOL_CONTENT_BYTES])
    rendered = "\n".join(out)
    if len(rendered.encode("utf-8", errors="replace")) > MAX_TOOL_CONTENT_BYTES:
        rendered = rendered[:MAX_TOOL_CONTENT_BYTES] + "\n[truncated]"
    return rendered


# ---- DB-facing helpers used by routes/connectors.py -----------------------

async def add_server(
    user_email: str, name: str, url: str, auth_header: str | None,
) -> dict[str, Any]:
    """Register a new MCP server, validate it by fetching its tool catalog."""
    if not user_email or not name or not url.startswith("http"):
        raise McpError("name + http(s) URL required")
    tools = await list_tools(url, auth_header)
    server_id = _gen_id()
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "user_email": user_email,
        "server_id": server_id,
        "name": name,
        "url": url,
        "auth_header": auth_header or None,
        "tools_cache": tools,
        "enabled": True,
        "last_error": None,
        "created_at": now,
        "updated_at": now,
    }
    await collection("mcp_servers").insert_one(dict(doc))
    return {"server_id": server_id, "name": name, "tools": tools}


async def list_servers(user_email: str) -> list[dict[str, Any]]:
    cursor = collection("mcp_servers").find(
        {"user_email": user_email},
        {"_id": 0, "auth_header": 0},  # never leak the auth back to the client
    )
    return await cursor.to_list(length=50)


async def delete_server(user_email: str, server_id: str) -> None:
    await collection("mcp_servers").delete_one(
        {"user_email": user_email, "server_id": server_id},
    )


async def refresh_server(user_email: str, server_id: str) -> list[dict[str, Any]]:
    row = await collection("mcp_servers").find_one(
        {"user_email": user_email, "server_id": server_id}
    )
    if not row:
        raise McpError("server not found")
    try:
        tools = await list_tools(row["url"], row.get("auth_header"))
    except McpError as error:
        await collection("mcp_servers").update_one(
            {"user_email": user_email, "server_id": server_id},
            {"$set": {"last_error": str(error)[:240], "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        raise
    await collection("mcp_servers").update_one(
        {"user_email": user_email, "server_id": server_id},
        {"$set": {
            "tools_cache": tools,
            "last_error": None,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
    )
    return tools


async def get_active_servers(user_email: str) -> list[dict[str, Any]]:
    """Servers we will inject into Aria's system prompt this turn."""
    if not user_email:
        return []
    return await collection("mcp_servers").find(
        {"user_email": user_email, "enabled": True},
    ).to_list(length=20)


def render_mcp_prompt(servers: list[dict[str, Any]]) -> str:
    """Render the system-prompt section enumerating MCP tools.

    Aria invokes them by emitting `[MCP_CALL: <server_id>:<tool_name> {json args}]`
    on its own line. The dispatcher in `chat_pipeline.py` picks those up and
    routes to `call_tool`.
    """
    if not servers:
        return ""
    chunks: list[str] = ["[MCP TOOLS — these come from servers the user connected]"]
    for server in servers:
        sid = server.get("server_id") or "?"
        name = server.get("name") or "?"
        chunks.append(f"\nServer: {name} (id={sid})")
        for tool in (server.get("tools_cache") or [])[:30]:
            tname = tool.get("name") or "?"
            desc = (tool.get("description") or "(no description)")[:160]
            chunks.append(f"  • {sid}:{tname} — {desc}")
    chunks.append(
        "\nInvoke any of these by emitting on its own line:\n"
        '  [MCP_CALL: <server_id>:<tool_name> {"arg1":"value","arg2":42}]\n'
        "Args MUST be a single JSON object. Result will be injected as a TOOL_RESULT."
    )
    return "\n".join(chunks)


async def dispatch_mcp_call(user_email: str, server_id: str, tool_name: str, args: dict[str, Any]) -> str:
    """Used by chat_pipeline when an MCP_CALL marker is parsed in Aria's reply."""
    row = await collection("mcp_servers").find_one(
        {"user_email": user_email, "server_id": server_id, "enabled": True}
    )
    if not row:
        return f"ERROR: MCP server {server_id} not connected or disabled."
    try:
        return await call_tool(row["url"], row.get("auth_header"), tool_name, args)
    except McpError as error:
        return f"ERROR: MCP call failed — {str(error)[:240]}"

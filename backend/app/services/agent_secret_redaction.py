from __future__ import annotations

import re
from typing import Any

_PATTERNS = [
    re.compile(r"(api[_-]?key\s*[=:]\s*)([^\s,;]+)", re.I),
    re.compile(r"(token\s*[=:]\s*)([^\s,;]+)", re.I),
    re.compile(r"(password\s*[=:]\s*)([^\s,;]+)", re.I),
    re.compile(r"(bearer\s+)([A-Za-z0-9\-\._~\+/]+=*)", re.I),
]


def _mask(value: str) -> str:
    if len(value) <= 4:
        return "****"
    return value[:2] + "***" + value[-2:]


def redact_secrets_text(text: str) -> str:
    out = text or ""
    for rx in _PATTERNS:
        out = rx.sub(lambda m: f"{m.group(1)}{_mask(m.group(2))}", out)
    return out


def redact_secrets(data: Any) -> Any:
    if isinstance(data, str):
        return redact_secrets_text(data)
    if isinstance(data, dict):
        return {k: redact_secrets(v) for k, v in data.items()}
    if isinstance(data, list):
        return [redact_secrets(v) for v in data]
    return data

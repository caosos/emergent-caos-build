"""Model catalog — single source of truth for context windows + USD pricing.

Keep this map current. Prices are in USD per 1M tokens, input / output.
Context window is the model's maximum context (prompt + response combined).

Lookups are forgiving: `find("claude-sonnet-4.5")`, `find("anthropic:claude-sonnet-4.5")`,
`find("gemini-3-flash-preview")` all resolve to the right entry. Unknown models
fall back to a conservative default (200 k ctx, $2.50/$10.00) so the app keeps
working when a new model appears mid-release.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelSpec:
    provider: str          # "openai" | "anthropic" | "gemini" | "xai"
    model: str             # canonical model id
    context_window: int    # max tokens (prompt + response)
    price_in_per_m: float  # USD per 1M input tokens
    price_out_per_m: float # USD per 1M output tokens
    label: str | None = None


# Populate from public pricing pages; verify periodically.
CATALOG: list[ModelSpec] = [
    # OpenAI
    ModelSpec("openai", "gpt-5.2",            400_000,  5.00, 15.00, "GPT-5.2"),
    ModelSpec("openai", "gpt-5.1",            400_000,  5.00, 15.00, "GPT-5.1"),
    ModelSpec("openai", "gpt-5",              400_000,  5.00, 15.00, "GPT-5"),
    ModelSpec("openai", "gpt-4o",             128_000,  2.50, 10.00, "GPT-4o"),
    ModelSpec("openai", "gpt-4o-mini",        128_000,  0.15,  0.60, "GPT-4o mini"),
    ModelSpec("openai", "o1",                 200_000, 15.00, 60.00, "OpenAI o1"),
    ModelSpec("openai", "o1-mini",            128_000,  3.00, 12.00, "o1-mini"),
    ModelSpec("openai", "o3-mini",            200_000,  1.10,  4.40, "o3-mini"),
    ModelSpec("openai", "gpt-image-1",        128_000,  5.00, 40.00, "GPT Image 1"),

    # Anthropic
    ModelSpec("anthropic", "claude-sonnet-4.5", 1_000_000,  3.00, 15.00, "Claude Sonnet 4.5"),
    ModelSpec("anthropic", "claude-opus-4.5",     200_000, 15.00, 75.00, "Claude Opus 4.5"),
    ModelSpec("anthropic", "claude-haiku-4.5",    200_000,  0.80,  4.00, "Claude Haiku 4.5"),
    ModelSpec("anthropic", "claude-sonnet-4",     200_000,  3.00, 15.00, "Claude Sonnet 4"),
    ModelSpec("anthropic", "claude-opus-4",       200_000, 15.00, 75.00, "Claude Opus 4"),
    ModelSpec("anthropic", "claude-3-5-sonnet-20241022", 200_000, 3.00, 15.00, "Claude 3.5 Sonnet"),

    # Gemini
    ModelSpec("gemini", "gemini-3-pro",        1_000_000,  1.25,  5.00, "Gemini 3 Pro"),
    ModelSpec("gemini", "gemini-3-flash",      1_000_000,  0.075, 0.30, "Gemini 3 Flash"),
    ModelSpec("gemini", "gemini-3-flash-preview", 1_000_000, 0.075, 0.30, "Gemini 3 Flash (preview)"),
    ModelSpec("gemini", "gemini-2.5-pro",       2_000_000, 1.25,  5.00, "Gemini 2.5 Pro"),
    ModelSpec("gemini", "gemini-2.5-flash",     1_000_000, 0.075, 0.30, "Gemini 2.5 Flash"),
    ModelSpec("gemini", "gemini-2.0-flash",     1_000_000, 0.075, 0.30, "Gemini 2.0 Flash"),

    # xAI
    ModelSpec("xai", "grok-4",                   256_000, 3.00, 15.00, "Grok 4"),
    ModelSpec("xai", "grok-2",                   131_072, 2.00, 10.00, "Grok 2"),
]

DEFAULT_SPEC = ModelSpec("unknown", "unknown", 200_000, 2.50, 10.00, "Unknown model")

# Build a lookup by canonical model id
_BY_MODEL = {spec.model: spec for spec in CATALOG}
# Build a provider-prefixed lookup (`openai:gpt-5.2` -> spec)
_BY_PROVIDER_MODEL = {f"{spec.provider}:{spec.model}": spec for spec in CATALOG}


def _normalize(name: str) -> str:
    return (name or "").strip().lower()


def find(identifier: str | None) -> ModelSpec:
    """Resolve `model`, `provider:model`, or a fuzzy tail (e.g. `claude-sonnet-4.5-20250927`).

    Tries exact match first, then provider-prefixed match, then substring/startswith
    fallback. Always returns a spec (falls back to DEFAULT_SPEC on miss).
    """
    if not identifier:
        return DEFAULT_SPEC
    norm = _normalize(identifier)
    if norm in _BY_PROVIDER_MODEL:
        return _BY_PROVIDER_MODEL[norm]
    if norm in _BY_MODEL:
        return _BY_MODEL[norm]
    # Strip provider prefix if present (e.g. "anthropic:claude-sonnet-4.5-20250927")
    model_part = norm.split(":", 1)[-1]
    if model_part in _BY_MODEL:
        return _BY_MODEL[model_part]
    # Fuzzy — longest startswith match wins
    candidates = [spec for spec in CATALOG if model_part.startswith(spec.model) or spec.model.startswith(model_part)]
    if candidates:
        return max(candidates, key=lambda s: len(s.model))
    return DEFAULT_SPEC


def context_window_for(identifier: str | None) -> int:
    return find(identifier).context_window


def compute_cost_usd(identifier: str | None, prompt_tokens: int, completion_tokens: int) -> float:
    spec = find(identifier)
    return round(
        (prompt_tokens or 0) * spec.price_in_per_m / 1_000_000
        + (completion_tokens or 0) * spec.price_out_per_m / 1_000_000,
        6,
    )


def public_catalog() -> list[dict]:
    """Shape used by the frontend — safe to serialize directly."""
    return [
        {
            "provider": spec.provider,
            "model": spec.model,
            "label": spec.label or spec.model,
            "context_window": spec.context_window,
            "price_in_per_m": spec.price_in_per_m,
            "price_out_per_m": spec.price_out_per_m,
        }
        for spec in CATALOG
    ]

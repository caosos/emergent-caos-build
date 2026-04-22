import os

from app.schemas.caos import RuntimePreferences, RuntimeProviderRecord, RuntimeSettingsResponse, UserProfileRecord


PROVIDER_DEFAULTS = {
    "openai": {"label": "ChatGPT", "model": "gpt-5.2", "requires_custom_key": False},
    "anthropic": {"label": "Claude", "model": "claude-sonnet-4-5-20250929", "requires_custom_key": False},
    "gemini": {"label": "Gemini", "model": "gemini-3-flash-preview", "requires_custom_key": False},
    "xai": {"label": "Grok", "model": "grok-byo-placeholder", "requires_custom_key": True},
}
UNIVERSAL_PROVIDERS = {"openai", "anthropic", "gemini"}
PROVIDER_ALIASES = {"grok": "xai"}


def canonical_provider(provider: str | None) -> str:
    value = (provider or "openai").strip().lower()
    return PROVIDER_ALIASES.get(value, value)


def get_provider_catalog(enabled_providers: list[str] | None = None) -> list[RuntimeProviderRecord]:
    enabled = {canonical_provider(item) for item in (enabled_providers or PROVIDER_DEFAULTS)}
    catalog: list[RuntimeProviderRecord] = []
    for provider, config in PROVIDER_DEFAULTS.items():
        if provider not in enabled:
            continue
        catalog.append(RuntimeProviderRecord(
            provider=provider,
            label=config["label"],
            default_model=config["model"],
            available=provider in UNIVERSAL_PROVIDERS,
            requires_custom_key=config["requires_custom_key"],
            key_status="needs-key" if config["requires_custom_key"] else "ready",
        ))
    return catalog


def build_runtime_settings_response(user_email: str, preferences: RuntimePreferences) -> RuntimeSettingsResponse:
    return RuntimeSettingsResponse(
        user_email=user_email,
        key_source=preferences.key_source,
        default_provider=canonical_provider(preferences.default_provider),
        default_model=preferences.default_model,
        enabled_providers=[canonical_provider(item) for item in preferences.enabled_providers],
        provider_catalog=get_provider_catalog(preferences.enabled_providers),
    )


def resolve_chat_runtime(profile: UserProfileRecord, requested_provider: str | None, requested_model: str | None) -> dict:
    preferences = profile.runtime_preferences or RuntimePreferences()
    provider = canonical_provider(requested_provider or preferences.default_provider)
    if provider not in PROVIDER_DEFAULTS:
        raise ValueError(f"Provider '{provider}' is not configured in CAOS yet")
    model = requested_model or preferences.default_model or PROVIDER_DEFAULTS[provider]["model"]
    if provider in UNIVERSAL_PROVIDERS:
        if preferences.key_source == "custom":
            raise ValueError(f"{provider} is set to custom mode, but custom provider keys are not attached yet")
        return {
            "provider": provider,
            "model": model,
            "api_key": os.environ["EMERGENT_LLM_KEY"],
            "key_source": "universal",
        }
    raise ValueError(
        "Grok/xAI is registered as a bring-your-own provider placeholder. Attach xAI credentials before selecting it for live inference"
    )


def supports_temperature_param(provider: str | None, model: str | None) -> bool:
    active_provider = canonical_provider(provider)
    active_model = (model or "").strip().lower()
    if active_provider != "openai":
        return True
    if active_model.startswith("gpt-5") and "chat" not in active_model:
        return False
    return True
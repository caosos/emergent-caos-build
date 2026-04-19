const FALLBACK_OPTIONS = [
  { provider: "openai", label: "ChatGPT", default_model: "gpt-5.2", available: true, requires_custom_key: false },
  { provider: "anthropic", label: "Claude", default_model: "claude-sonnet-4-5-20250929", available: true, requires_custom_key: false },
  { provider: "gemini", label: "Gemini", default_model: "gemini-3-flash-preview", available: true, requires_custom_key: false },
  { provider: "xai", label: "Grok", default_model: "grok-byo-placeholder", available: false, requires_custom_key: true },
];


export const ModelBar = ({ activeModel, activeProvider, keySource, onSelect, providerCatalog }) => {
  const options = providerCatalog?.length ? providerCatalog : FALLBACK_OPTIONS;

  return (
    <div className="model-bar-shell" data-testid="caos-model-bar-shell">
      <div className="model-bar" data-testid="caos-model-bar">
        <span className="model-bar-label" data-testid="caos-model-bar-label">Model</span>
        <button className="model-bar-mode-button" data-testid="caos-model-mode-button" type="button">
          <span>Smart Auto</span>
          <small>{keySource || "hybrid"}</small>
        </button>
        {options.map((option) => {
          const isDisabled = option.requires_custom_key && !option.available;
          const isActive = option.provider === activeProvider && option.default_model === activeModel;

          return (
            <button
              className={`model-chip ${isActive ? "model-chip-active" : "model-chip-disabled"}`}
              data-testid={`caos-model-chip-${option.provider}`}
              disabled={isDisabled}
              key={option.provider}
              onClick={() => onSelect(option.provider, option.default_model)}
              title={isDisabled ? `${option.label} is staged for BYO credentials` : `${option.label} · ${option.default_model}`}
              type="button"
            >
              <span>{option.label}</span>
              <small>{isDisabled ? "Bring key" : option.default_model.replace("-preview", "")}</small>
            </button>
          );
        })}
        <button className="model-more-button" data-testid="caos-model-more-button" type="button">More</button>
      </div>
    </div>
  );
};
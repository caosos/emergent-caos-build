import { useEffect, useRef, useState } from "react";
import { Zap } from "lucide-react";

const LABELS = { openai: "OpenAI", anthropic: "Claude", gemini: "Gemini", xai: "Grok" };
const DEFAULT_OPTIONS = [
  { provider: "anthropic", label: "Claude", default_model: "claude-sonnet-4-5-20250929", available: true, requires_custom_key: false },
  { provider: "openai", label: "OpenAI", default_model: "gpt-5.2", available: true, requires_custom_key: false },
  { provider: "gemini", label: "Gemini", default_model: "gemini-3-flash-preview", available: true, requires_custom_key: false },
  { provider: "xai", label: "Grok", default_model: "grok-byo-placeholder", available: false, requires_custom_key: true },
];

export const EngineChip = ({ activeProvider, activeModel, providerCatalog, onSelect }) => {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef(null);
  const options = providerCatalog?.length ? providerCatalog : DEFAULT_OPTIONS;
  const label = LABELS[activeProvider] || "OpenAI";

  useEffect(() => {
    if (!isOpen) return undefined;
    const handler = (event) => {
      if (ref.current && !ref.current.contains(event.target)) setIsOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [isOpen]);

  return (
    <div className="engine-chip-shell" data-testid="caos-engine-chip-shell" ref={ref}>
      <button
        className="engine-chip"
        data-testid="caos-engine-chip"
        onClick={() => setIsOpen((value) => !value)}
        title={`Engine: ${label} — click to switch`}
        type="button"
      >
        <Zap size={13} />
        <strong data-testid="caos-engine-chip-label">{label}</strong>
        <span className="engine-chip-hint" data-testid="caos-engine-chip-hint">click to switch</span>
      </button>
      {isOpen ? (
        <div className="engine-chip-menu" data-testid="caos-engine-chip-menu" role="menu">
          {options.map((option) => {
            const disabled = option.requires_custom_key && !option.available;
            const active = option.provider === activeProvider && option.default_model === activeModel;
            return (
              <button
                className={`engine-chip-menu-item ${active ? "engine-chip-menu-item-active" : ""}`}
                data-testid={`caos-engine-chip-option-${option.provider}`}
                disabled={disabled}
                key={option.provider}
                onClick={() => {
                  if (disabled) return;
                  onSelect(option.provider, option.default_model);
                  setIsOpen(false);
                }}
                type="button"
              >
                <strong>{option.label}</strong>
                <span>{disabled ? "Bring your own key" : option.default_model.replace("-preview", "")}</span>
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
};

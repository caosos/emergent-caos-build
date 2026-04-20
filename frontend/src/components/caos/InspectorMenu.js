import { useEffect, useRef, useState } from "react";
import { ChevronRight, History, LogOut, Menu, Monitor, PlusCircle, Sparkles, UserCircle, Zap } from "lucide-react";

const LABELS = { openai: "OpenAI", anthropic: "Claude", gemini: "Gemini", xai: "Grok" };

/**
 * Base44-parity left inspector menu. Triggered by a hamburger button; shows:
 *   - Desktop (current workspace label, non-interactive)
 *   - + New Thread
 *   - Previous Threads
 *   - Profile
 *   - Engine (inline — clicking expands a sub-menu of providers)
 *   - Log Out
 */
export const InspectorMenu = ({ activeProvider, activeModel, onLogOut, onNewThread, onOpenProfile, onOpenThreads, onSelectProvider, providerCatalog }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [engineSubOpen, setEngineSubOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!isOpen) return undefined;
    const handler = (event) => {
      if (ref.current && !ref.current.contains(event.target)) {
        setIsOpen(false);
        setEngineSubOpen(false);
      }
    };
    const esc = (event) => { if (event.key === "Escape") { setIsOpen(false); setEngineSubOpen(false); } };
    document.addEventListener("mousedown", handler);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", handler);
      document.removeEventListener("keydown", esc);
    };
  }, [isOpen]);

  const engineLabel = LABELS[activeProvider] || "OpenAI";

  const pick = (fn) => () => {
    fn?.();
    setIsOpen(false);
    setEngineSubOpen(false);
  };

  return (
    <div className="inspector-menu-shell" data-testid="caos-inspector-menu-shell" ref={ref}>
      <button
        aria-label="Open inspector menu"
        className="inspector-menu-trigger"
        data-testid="caos-inspector-menu-trigger"
        onClick={() => setIsOpen((value) => !value)}
        type="button"
      >
        <Menu size={14} />
      </button>
      {isOpen ? (
        <div className="inspector-menu" data-testid="caos-inspector-menu" role="menu">
          <div className="inspector-menu-header" data-testid="caos-inspector-menu-header">
            <Monitor size={13} />
            <span>Desktop</span>
          </div>
          <button
            className="inspector-menu-item inspector-menu-item-primary"
            data-testid="caos-inspector-menu-new-thread"
            onClick={pick(onNewThread)}
            type="button"
          >
            <PlusCircle size={14} />
            <span>New Thread</span>
          </button>
          <button
            className="inspector-menu-item"
            data-testid="caos-inspector-menu-previous-threads"
            onClick={pick(onOpenThreads)}
            type="button"
          >
            <History size={14} />
            <span>Previous Threads</span>
          </button>
          <button
            className="inspector-menu-item"
            data-testid="caos-inspector-menu-profile"
            onClick={pick(onOpenProfile)}
            type="button"
          >
            <UserCircle size={14} />
            <span>Profile</span>
          </button>
          <div className="inspector-menu-engine-row" data-testid="caos-inspector-menu-engine-row">
            <button
              className={`inspector-menu-item inspector-menu-item-engine ${engineSubOpen ? "inspector-menu-item-active" : ""}`}
              data-testid="caos-inspector-menu-engine-button"
              onClick={() => setEngineSubOpen((value) => !value)}
              type="button"
            >
              <Zap size={14} className="inspector-menu-engine-icon" />
              <span>Engine</span>
              <strong className="inspector-menu-engine-label" data-testid="caos-inspector-menu-engine-active">{engineLabel}</strong>
              <ChevronRight size={12} className={engineSubOpen ? "inspector-menu-chevron-open" : ""} />
            </button>
            {engineSubOpen ? (
              <div className="inspector-menu-engine-sub" data-testid="caos-inspector-menu-engine-sub">
                {(providerCatalog || []).map((option) => {
                  const disabled = option.requires_custom_key && !option.available;
                  const active = option.provider === activeProvider && option.default_model === activeModel;
                  return (
                    <button
                      className={`inspector-menu-sub-item ${active ? "inspector-menu-sub-item-active" : ""}`}
                      data-testid={`caos-inspector-menu-engine-option-${option.provider}`}
                      disabled={disabled}
                      key={option.provider}
                      onClick={() => {
                        if (disabled) return;
                        onSelectProvider?.(option.provider, option.default_model);
                        setIsOpen(false);
                        setEngineSubOpen(false);
                      }}
                      type="button"
                    >
                      <Sparkles size={11} />
                      <span>{option.label}</span>
                      <em>{disabled ? "BYO key" : option.default_model.replace("-preview", "")}</em>
                    </button>
                  );
                })}
              </div>
            ) : null}
          </div>
          <div className="inspector-menu-divider" />
          <button
            className="inspector-menu-item inspector-menu-item-danger"
            data-testid="caos-inspector-menu-logout"
            onClick={pick(onLogOut)}
            type="button"
          >
            <LogOut size={14} />
            <span>Log Out</span>
          </button>
        </div>
      ) : null}
    </div>
  );
};

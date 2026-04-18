import { Cpu, PanelLeftClose, PanelLeftOpen, Search } from "lucide-react";


const PROVIDER_LABELS = {
  openai: "ChatGPT",
  anthropic: "Claude",
  gemini: "Gemini",
  xai: "Grok",
};


export const ShellHeader = ({ activeModel, activeProvider, currentSession, isRailOpen, keySource, onToggleRail, onToggleSearch, wcwBudget, wcwUsed }) => {
  const percent = Math.min(100, Math.round(((wcwUsed || 0) / (wcwBudget || 1)) * 100));
  const providerLabel = PROVIDER_LABELS[activeProvider] || activeProvider || "ChatGPT";

  return (
    <header className="caos-header" data-testid="caos-shell-header">
      <div className="caos-header-context" data-testid="caos-header-context">
        <div>
          <h1 data-testid="caos-header-title">{currentSession?.title || "Chat"}</h1>
          <p data-testid="caos-header-subtitle">{currentSession?.session_id || "Start a thread from the left rail."}</p>
        </div>
      </div>

      <div className="caos-header-actions">
        <button className="search-icon-button" data-testid="caos-rail-toggle-button" onClick={onToggleRail}>
          {isRailOpen ? <PanelLeftClose size={14} /> : <PanelLeftOpen size={14} />}
        </button>

        <button className="search-icon-button" data-testid="caos-search-toggle-button" onClick={onToggleSearch}>
          <Search size={14} />
        </button>

        <div className="engine-chip" data-testid="caos-engine-chip">
          <Cpu size={14} />
          <span>{providerLabel} · {activeModel}</span>
          <small data-testid="caos-engine-key-source">{keySource}</small>
        </div>

        <div className="token-chip" data-testid="caos-token-meter">
          <span>{wcwUsed || 0} / {wcwBudget || 200000}</span>
          <div className="token-bar" data-testid="caos-token-meter-bar">
            <div className="token-bar-fill" style={{ width: `${percent}%` }} />
          </div>
        </div>
      </div>
    </header>
  );
};
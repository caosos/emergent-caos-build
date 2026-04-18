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
      <div className="caos-header-left" data-testid="caos-header-left">
        <button className="search-icon-button" data-testid="caos-rail-toggle-button" onClick={onToggleRail}>
          {isRailOpen ? <PanelLeftClose size={14} /> : <PanelLeftOpen size={14} />}
        </button>
        <div className="caos-header-route" data-testid="caos-header-route">Chat surface</div>
      </div>

      <div className="caos-header-center" data-testid="caos-header-center">
        <h1 data-testid="caos-header-title">CAOS</h1>
        <p data-testid="caos-header-subtitle">Cognitive Adaptive Operating System</p>
      </div>

      <div className="caos-header-actions">
        <div className="caos-thread-pill" data-testid="caos-header-thread-pill">{currentSession?.title || "No active thread"}</div>

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
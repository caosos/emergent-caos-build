import { PanelLeftClose, PanelLeftOpen, Search } from "lucide-react";

import { InspectorMenu } from "@/components/caos/InspectorMenu";

const formatTokens = (value) => {
  const numeric = Number(value) || 0;
  if (numeric >= 1000000) return `${(numeric / 1000000).toFixed(1)}M`;
  if (numeric >= 1000) return `${(numeric / 1000).toFixed(1)}K`;
  return `${numeric}`;
};

/**
 * Base44-parity header: 3-column layout.
 * Left  : rail toggle + inspector menu (hamburger) + user identity chip (click opens Profile)
 * Center: CAOS title + "Cognitive Adaptive Operating System" subtitle
 * Right : active thread pill + search icon + live WCW meter
 *
 * Single-source-of-truth menu model: ALL navigation lives in the hamburger.
 * The identity chip is a visual shortcut only — click it to open the Profile
 * panel directly (not another dropdown).
 */
export const ShellHeader = ({
  activeProvider,
  activeModel,
  authenticatedUser,
  currentSession,
  displayName,
  isRailOpen,
  onLogOut,
  onNewThread,
  onOpenProfile,
  onOpenSwarm,
  onOpenThreads,
  onSelectProvider,
  onToggleRail,
  onToggleSearch,
  providerCatalog,
  wcwBudget,
  wcwUsed,
}) => {
  const percent = Math.min(100, Math.round(((wcwUsed || 0) / (wcwBudget || 1)) * 100));

  return (
    <header className="caos-header" data-testid="caos-shell-header">
      <div className="caos-header-left" data-testid="caos-header-left">
        <button className="search-icon-button" data-testid="caos-rail-toggle-button" onClick={onToggleRail}>
          {isRailOpen ? <PanelLeftClose size={14} /> : <PanelLeftOpen size={14} />}
        </button>
        <InspectorMenu
          activeModel={activeModel}
          activeProvider={activeProvider}
          onLogOut={onLogOut}
          onNewThread={onNewThread}
          onOpenProfile={onOpenProfile}
          onOpenSwarm={onOpenSwarm}
          onOpenThreads={onOpenThreads}
          onSelectProvider={onSelectProvider}
          providerCatalog={providerCatalog}
        />
        <div className="caos-header-identity" data-testid="caos-header-identity">
          <button
            className="caos-header-identity-chip"
            data-testid="caos-header-identity-chip"
            onClick={() => onOpenProfile?.()}
            title={authenticatedUser?.email || "Open profile"}
            type="button"
          >
            <span className="caos-header-identity-avatar" data-testid="caos-header-identity-avatar">
              {authenticatedUser?.picture ? (
                <img src={authenticatedUser.picture} alt="" width="22" height="22" style={{ borderRadius: "50%", display: "block" }} />
              ) : (
                (displayName || "M").trim().charAt(0).toUpperCase()
              )}
            </span>
            <strong data-testid="caos-header-identity-name">{(authenticatedUser?.name || displayName || "Michael").toUpperCase()}</strong>
          </button>
        </div>
      </div>

      <div className="caos-header-center" data-testid="caos-header-center">
        <h1 data-testid="caos-header-title">CAOS</h1>
        <p data-testid="caos-header-subtitle">Cognitive Adaptive Operating System</p>
      </div>

      <div className="caos-header-actions" data-testid="caos-header-actions">
        <button className="caos-thread-pill" data-testid="caos-header-thread-pill" onClick={onOpenThreads} type="button">
          {currentSession?.title || "Start a new chat"}
        </button>
        <button className="search-icon-button" data-testid="caos-search-toggle-button" onClick={onToggleSearch} title="Search thread">
          <Search size={14} />
        </button>
        <div className="caos-header-wcw" data-testid="caos-header-wcw" title="Working Context Window (live)">
          <span data-testid="caos-header-wcw-used">{formatTokens(wcwUsed)}</span>
          <span className="caos-header-wcw-divider">/</span>
          <span data-testid="caos-header-wcw-budget">{formatTokens(wcwBudget)}</span>
          <div className="caos-header-wcw-bar" data-testid="caos-header-wcw-bar">
            <div className="caos-header-wcw-fill" style={{ width: `${percent}%` }} />
          </div>
        </div>
      </div>
    </header>
  );
};

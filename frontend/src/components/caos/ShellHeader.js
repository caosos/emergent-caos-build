import { PanelLeftClose, PanelLeftOpen, Search } from "lucide-react";

import { AccountMenu } from "@/components/caos/AccountMenu";

const formatTokens = (value) => {
  const numeric = Number(value) || 0;
  if (numeric >= 1000000) return `${(numeric / 1000000).toFixed(1)}M`;
  if (numeric >= 1000) return `${(numeric / 1000).toFixed(1)}K`;
  return `${numeric}`;
};

/**
 * Base44-parity header: 3-column layout.
 * Left  : rail toggle + AccountMenu (the identity chip IS the menu trigger)
 * Center: CAOS title + subtitle
 * Right : active thread pill + search icon + live WCW meter
 *
 * Per UX_BLUEPRINT §C — single dropdown. No separate hamburger.
 */
export const ShellHeader = ({
  activeProvider,
  activeModel,
  authenticatedUser,
  currentSession,
  displayName,
  isAdmin,
  isRailOpen,
  onLogOut,
  onNewThread,
  onOpenAdminDocs,
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
        <AccountMenu
          activeModel={activeModel}
          activeProvider={activeProvider}
          authenticatedUser={authenticatedUser}
          displayName={displayName}
          isAdmin={isAdmin}
          onLogOut={onLogOut}
          onNewThread={onNewThread}
          onOpenAdminDocs={onOpenAdminDocs}
          onOpenProfile={onOpenProfile}
          onOpenSwarm={onOpenSwarm}
          onOpenThreads={onOpenThreads}
          onSelectProvider={onSelectProvider}
          providerCatalog={providerCatalog}
        />
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

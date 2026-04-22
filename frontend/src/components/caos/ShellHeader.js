import { PanelLeftClose, PanelLeftOpen, Search, X } from "lucide-react";

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
 * Right : active thread pill + inline search box + live WCW meter
 *
 * The search input lives INSIDE the header. Typing drives `searchQuery`;
 * the right-side panel mounts automatically when the query is non-empty.
 */
export const ShellHeader = ({
  activeProvider,
  activeModel,
  authenticatedUser,
  currentSession,
  displayName,
  isAdmin,
  isRailOpen,
  matchCount,
  onLogOut,
  onNewThread,
  onOpenAdminDocs,
  onOpenProfile,
  onOpenSwarm,
  onOpenThreads,
  onSelectProvider,
  onToggleRail,
  providerCatalog,
  searchQuery,
  setSearchQuery,
  wcwBudget,
  wcwUsed,
}) => {
  const percent = Math.min(100, Math.round(((wcwUsed || 0) / (wcwBudget || 1)) * 100));
  const hasQuery = (searchQuery || "").trim().length > 0;

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
        <div className={`caos-header-search-inline ${hasQuery ? "caos-header-search-inline-active" : ""}`} data-testid="caos-header-search-inline">
          <Search size={13} />
          <input
            aria-label="Search this thread"
            data-testid="caos-header-search-input"
            onChange={(event) => setSearchQuery?.(event.target.value)}
            placeholder="fre…"
            type="text"
            value={searchQuery || ""}
          />
          {hasQuery ? (
            <>
              <span className="caos-header-search-count" data-testid="caos-header-search-count">{matchCount || 0}</span>
              <button
                aria-label="Clear search"
                className="caos-header-search-clear"
                data-testid="caos-header-search-clear-button"
                onClick={() => setSearchQuery?.("")}
                type="button"
              ><X size={12} /></button>
            </>
          ) : null}
        </div>
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

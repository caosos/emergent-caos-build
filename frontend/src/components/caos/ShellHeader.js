import { Search, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { AccountMenu } from "@/components/caos/AccountMenu";

const formatTokens = (value) => {
  const numeric = Number(value) || 0;
  if (numeric >= 1000000) return `${(numeric / 1000000).toFixed(1)}M`;
  if (numeric >= 1000) return `${(numeric / 1000).toFixed(1)}K`;
  return `${numeric}`;
};

/**
 * Base44-parity header:
 * Left  : AccountMenu chip (single dropdown, no rail toggle)
 * Center: CAOS title + search icon underneath that opens a popover dropdown
 * Right : thread pill + live WCW meter
 */
export const ShellHeader = ({
  activeProvider,
  activeModel,
  authenticatedUser,
  currentSession,
  displayName,
  isAdmin,
  matchCount,
  onLogOut,
  onNewThread,
  onOpenAdminDocs,
  onOpenFiles,
  onOpenProfile,
  onOpenSwarm,
  onOpenThreads,
  onSelectProvider,
  providerCatalog,
  searchQuery,
  setSearchQuery,
  wcwBudget,
  wcwUsed,
}) => {
  const percent = Math.min(100, Math.round(((wcwUsed || 0) / (wcwBudget || 1)) * 100));
  const hasQuery = (searchQuery || "").trim().length > 0;
  const [searchOpen, setSearchOpen] = useState(false);
  const searchPopoverRef = useRef(null);

  useEffect(() => {
    if (!searchOpen) return undefined;
    const onClickOutside = (event) => {
      if (searchPopoverRef.current && !searchPopoverRef.current.contains(event.target)) {
        setSearchOpen(false);
      }
    };
    const onEsc = (event) => { if (event.key === "Escape") setSearchOpen(false); };
    document.addEventListener("mousedown", onClickOutside);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onClickOutside);
      document.removeEventListener("keydown", onEsc);
    };
  }, [searchOpen]);

  return (
    <header className="caos-header" data-testid="caos-shell-header">
      <div className="caos-header-left" data-testid="caos-header-left">
        <AccountMenu
          activeModel={activeModel}
          activeProvider={activeProvider}
          authenticatedUser={authenticatedUser}
          displayName={displayName}
          isAdmin={isAdmin}
          onLogOut={onLogOut}
          onNewThread={onNewThread}
          onOpenAdminDocs={onOpenAdminDocs}
          onOpenFiles={onOpenFiles}
          onOpenProfile={onOpenProfile}
          onOpenSwarm={onOpenSwarm}
          onOpenThreads={onOpenThreads}
          onSelectProvider={onSelectProvider}
          providerCatalog={providerCatalog}
        />
      </div>

      <div className="caos-header-center" data-testid="caos-header-center">
        <h1 data-testid="caos-header-title">CAOS</h1>
      </div>

      <div className="caos-header-actions" data-testid="caos-header-actions" ref={searchPopoverRef}>
        <span className="caos-thread-pill" data-testid="caos-header-thread-pill" title={currentSession?.title || "No active thread"}>
          {(currentSession?.title || "Start a new chat").split(/\s+/).slice(0, 3).join(" ")}
        </span>
        <div className="caos-header-search-wrap" data-testid="caos-header-search-wrap">
          <button
            aria-label="Search this thread"
            className={`caos-title-search-trigger ${hasQuery || searchOpen ? "caos-title-search-trigger-active" : ""}`}
            data-testid="caos-title-search-trigger"
            onClick={() => setSearchOpen((v) => !v)}
            title="Search this thread"
            type="button"
          >
            <Search size={12} />
          </button>
          {searchOpen ? (
            <div className="caos-title-search-popover caos-title-search-popover-right" data-testid="caos-title-search-popover">
              <Search size={12} />
              <input
                aria-label="Search this thread"
                autoFocus
                data-testid="caos-header-search-input"
                onChange={(event) => setSearchQuery?.(event.target.value)}
                placeholder="Search this thread…"
                type="text"
                value={searchQuery || ""}
              />
              {hasQuery ? (
                <>
                  <span className="caos-title-search-count" data-testid="caos-header-search-count" title={`${matchCount || 0} match${matchCount === 1 ? "" : "es"}`}>{matchCount || 0}</span>
                  <button
                    aria-label="Clear search"
                    className="caos-title-search-clear"
                    data-testid="caos-header-search-clear-button"
                    onClick={() => setSearchQuery?.("")}
                    title="Clear search"
                    type="button"
                  ><X size={12} /></button>
                </>
              ) : null}
            </div>
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

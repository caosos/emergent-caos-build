import { PanelLeftClose, PanelLeftOpen, Search } from "lucide-react";

const SURFACE_LABELS = {
  chat: "Chat",
  create: "Create",
  tools: "Tools",
  models: "Models",
  projects: "Projects",
  threads: "Threads",
  search: "Search",
};


export const ShellHeader = ({ activeSurface, currentSession, isRailOpen, onOpenThreads, onToggleRail, onToggleSearch }) => {
  const surfaceLabel = SURFACE_LABELS[activeSurface] || "Chat";

  return (
    <header className="caos-header" data-testid="caos-shell-header">
      <div className="caos-header-left" data-testid="caos-header-left">
        <button className="search-icon-button" data-testid="caos-rail-toggle-button" onClick={onToggleRail}>
          {isRailOpen ? <PanelLeftClose size={14} /> : <PanelLeftOpen size={14} />}
        </button>
        <div className="caos-header-route" data-testid="caos-header-route">{surfaceLabel}</div>
      </div>

      <div className="caos-header-center" data-testid="caos-header-center">
        <h1 data-testid="caos-header-title">CAOS</h1>
      </div>

      <div className="caos-header-actions">
        <button className="caos-thread-pill" data-testid="caos-header-thread-pill" onClick={onOpenThreads} type="button">{currentSession?.title || "Start a new chat"}</button>

        <button className="search-icon-button" data-testid="caos-search-toggle-button" onClick={onToggleSearch}>
          <Search size={14} />
        </button>
      </div>
    </header>
  );
};
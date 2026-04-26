import { useEffect, useRef, useState } from "react";
import { Bot, BookOpen, Brain, ChevronDown, ChevronRight, FileText, History, Image as ImageIcon, Inbox, LayoutDashboard, LifeBuoy, Link2, LogOut, Monitor, PlusCircle, Sparkles, UserCircle, Zap, Shield } from "lucide-react";

const LABELS = { openai: "OpenAI", anthropic: "Claude", gemini: "Gemini", xai: "Grok" };

/**
 * Base44-parity account menu. The user identity chip itself is the dropdown
 * trigger — no separate hamburger. Matches UX_BLUEPRINT §C exactly.
 *
 * Menu items:
 *   - Desktop (label, non-interactive)
 *   - + New Thread
 *   - Previous Threads
 *   - Profile
 *   - Engine → sub-menu of providers
 *   - Agent Swarm · E2B
 *   - Admin Docs (admin only)
 *   - Log Out
 */
export const AccountMenu = ({
  activeModel,
  activeProvider,
  authenticatedUser,
  displayName,
  isAdmin,
  onLogOut,
  onNewThread,
  onOpenAdminDashboard,
  onOpenAdminDocs,
  onOpenCaptures,
  onOpenFiles,
  onOpenMemory,
  onOpenProfile,
  onOpenSupport,
  onOpenSwarm,
  onOpenThreads,
  onSelectProvider,
  providerCatalog,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [engineSubOpen, setEngineSubOpen] = useState(false);
  const [desktopSubOpen, setDesktopSubOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!isOpen) return undefined;
    const outside = (event) => {
      if (ref.current && !ref.current.contains(event.target)) {
        setIsOpen(false);
        setEngineSubOpen(false);
        setDesktopSubOpen(false);
      }
    };
    const esc = (event) => { if (event.key === "Escape") { setIsOpen(false); setEngineSubOpen(false); setDesktopSubOpen(false); } };
    document.addEventListener("mousedown", outside);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", outside);
      document.removeEventListener("keydown", esc);
    };
  }, [isOpen]);

  const engineLabel = LABELS[activeProvider] || "OpenAI";
  const initial = (authenticatedUser?.name || displayName || "M").trim().charAt(0).toUpperCase();
  const name = (authenticatedUser?.name || displayName || "Michael").toUpperCase();

  const pick = (fn) => () => {
    fn?.();
    setIsOpen(false);
    setEngineSubOpen(false);
    setDesktopSubOpen(false);
  };

  return (
    <div className="account-menu-shell" data-testid="caos-account-menu-shell" ref={ref}>
      <button
        aria-label="Open account menu"
        className="account-menu-chip"
        data-testid="caos-account-menu-chip"
        onClick={() => setIsOpen((v) => !v)}
        type="button"
      >
        <span className="account-menu-avatar" data-testid="caos-account-menu-avatar">
          {authenticatedUser?.picture
            ? <img src={authenticatedUser.picture} alt="" width="22" height="22" style={{ borderRadius: "50%", display: "block" }} />
            : initial}
        </span>
        <strong data-testid="caos-account-menu-name">{name}</strong>
        <ChevronDown size={12} className={isOpen ? "account-menu-chevron-open" : ""} />
      </button>
      {isOpen ? (
        <div className="inspector-menu" data-testid="caos-account-menu" role="menu">
          <div className="inspector-menu-engine-row" data-testid="caos-account-menu-desktop-row">
            <button
              className={`inspector-menu-item inspector-menu-item-engine ${desktopSubOpen ? "inspector-menu-item-active" : ""}`}
              data-testid="caos-account-menu-desktop-button"
              onClick={() => setDesktopSubOpen((v) => !v)}
              type="button"
            >
              <Monitor size={14} />
              <span>Desktop</span>
              <ChevronRight size={12} className={desktopSubOpen ? "inspector-menu-chevron-open" : ""} style={{ marginLeft: "auto" }} />
            </button>
            {desktopSubOpen ? (
              <div className="inspector-menu-engine-sub" data-testid="caos-account-menu-desktop-sub">
                <button
                  className="inspector-menu-sub-item"
                  data-testid="caos-account-menu-desktop-files"
                  onClick={pick(() => { onOpenFiles?.("files"); })}
                  type="button"
                >
                  <FileText size={11} /><span>Files</span>
                </button>
                <button
                  className="inspector-menu-sub-item"
                  data-testid="caos-account-menu-desktop-photos"
                  onClick={pick(() => { onOpenFiles?.("photos"); })}
                  type="button"
                >
                  <ImageIcon size={11} /><span>Photos</span>
                </button>
                <button
                  className="inspector-menu-sub-item"
                  data-testid="caos-account-menu-desktop-links"
                  onClick={pick(() => { onOpenFiles?.("links"); })}
                  type="button"
                >
                  <Link2 size={11} /><span>Links</span>
                </button>
              </div>
            ) : null}
          </div>
          <button className="inspector-menu-item inspector-menu-item-primary" data-testid="caos-account-menu-new-thread" onClick={pick(onNewThread)} type="button">
            <PlusCircle size={14} /><span>New Thread</span>
          </button>
          <button className="inspector-menu-item" data-testid="caos-account-menu-previous-threads" onClick={pick(onOpenThreads)} type="button">
            <History size={14} /><span>Previous Threads</span>
          </button>
          <button className="inspector-menu-item" data-testid="caos-account-menu-profile" onClick={pick(onOpenProfile)} type="button">
            <UserCircle size={14} /><span>Settings</span>
          </button>
          <button className="inspector-menu-item" data-testid="caos-account-menu-memory" onClick={pick(onOpenMemory)} type="button">
            <Brain size={14} /><span>Memory Console</span>
            <em style={{ marginLeft: "auto", fontSize: 10, color: "rgba(167, 139, 250, 0.85)" }}>NEW</em>
          </button>
          <button className="inspector-menu-item" data-testid="caos-account-menu-captures" onClick={pick(onOpenCaptures)} type="button">
            <Inbox size={14} /><span>Quick Capture</span>
            <em style={{ marginLeft: "auto", fontSize: 10, color: "rgba(110, 231, 183, 0.95)" }}>NEW</em>
          </button>
          <div className="inspector-menu-engine-row" data-testid="caos-account-menu-engine-row">
            <button
              className={`inspector-menu-item inspector-menu-item-engine ${engineSubOpen ? "inspector-menu-item-active" : ""}`}
              data-testid="caos-account-menu-engine-button"
              onClick={() => setEngineSubOpen((v) => !v)}
              type="button"
            >
              <Zap size={14} className="inspector-menu-engine-icon" />
              <span>Engine</span>
              <strong className="inspector-menu-engine-label" data-testid="caos-account-menu-engine-active">{engineLabel}</strong>
              <ChevronRight size={12} className={engineSubOpen ? "inspector-menu-chevron-open" : ""} />
            </button>
            {engineSubOpen ? (
              <div className="inspector-menu-engine-sub" data-testid="caos-account-menu-engine-sub">
                {(providerCatalog || []).map((option) => {
                  const disabled = option.requires_custom_key && !option.available;
                  const active = option.provider === activeProvider && option.default_model === activeModel;
                  return (
                    <button
                      className={`inspector-menu-sub-item ${active ? "inspector-menu-sub-item-active" : ""}`}
                      data-testid={`caos-account-menu-engine-option-${option.provider}`}
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
                      <Sparkles size={11} /><span>{option.label}</span>
                      <em>{disabled ? "BYO key" : option.default_model.replace("-preview", "")}</em>
                    </button>
                  );
                })}
              </div>
            ) : null}
          </div>
          <button className="inspector-menu-item" data-testid="caos-account-menu-swarm" onClick={pick(onOpenSwarm)} type="button">
            <Bot size={14} /><span>Agent Swarm</span>
            <em style={{ marginLeft: "auto", fontSize: 10, color: "rgba(167, 139, 250, 0.7)" }}>E2B</em>
          </button>
          {isAdmin ? (
            <>
              <button className="inspector-menu-item" data-testid="caos-account-menu-admin-dashboard" onClick={pick(onOpenAdminDashboard)} type="button">
                <LayoutDashboard size={14} /><span>Admin Dashboard</span>
                <em style={{ marginLeft: "auto", fontSize: 10, color: "rgba(250, 204, 21, 0.8)" }}>ADMIN</em>
              </button>
              <button className="inspector-menu-item" data-testid="caos-account-menu-admin-docs" onClick={pick(onOpenAdminDocs)} type="button">
                <BookOpen size={14} /><span>Admin Docs</span>
                <em style={{ marginLeft: "auto", fontSize: 10, color: "rgba(250, 204, 21, 0.8)" }}>ADMIN</em>
              </button>
            </>
          ) : null}
          <button className="inspector-menu-item" data-testid="caos-account-menu-support" onClick={pick(onOpenSupport)} type="button">
            <LifeBuoy size={14} /><span>Support Tickets</span>
          </button>
          <div className="inspector-menu-divider" />
          <button
            className="inspector-menu-item inspector-menu-item-danger"
            data-testid="caos-account-menu-logout"
            onClick={pick(onLogOut)}
            type="button"
            title="Log out of this browser"
          >
            <LogOut size={14} /><span>Log Out</span>
          </button>
        </div>
      ) : null}
    </div>
  );
};

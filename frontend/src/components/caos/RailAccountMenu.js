import { ChevronDown, Copy, FolderOpen, ImagePlus, Link2, LogOut, Search, Settings2, Sparkles } from "lucide-react";
import { useMemo, useState } from "react";
import { createPortal } from "react-dom";


const labelForProvider = (provider) => ({ openai: "ChatGPT", anthropic: "Claude", gemini: "Gemini", xai: "Grok" }[provider] || provider || "ChatGPT");
const AVATAR_URL = "https://images.pexels.com/photos/5349053/pexels-photo-5349053.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940";


export const RailAccountMenu = ({ currentSessionId, displayName, email, isCollapsed, onNewSession, onOpenArtifacts, onOpenProfile, onOpenSearch, runtimeSettings, wcwBudget, wcwUsed, wcwSent, wcwReceived }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [menuStatus, setMenuStatus] = useState("");
  const engineLabel = useMemo(() => `${labelForProvider(runtimeSettings?.default_provider)} · ${runtimeSettings?.default_model || "gpt-5.2"}`, [runtimeSettings?.default_model, runtimeSettings?.default_provider]);
  const packetPercent = Math.min(100, Math.round(((wcwUsed || 0) / (wcwBudget || 1)) * 100));

  const copySessionToken = async () => {
    if (!currentSessionId) return setMenuStatus("Open a thread first to copy its token.");
    await navigator.clipboard.writeText(currentSessionId);
    setMenuStatus("Session token copied.");
  };

  const settingsItems = [
    { id: "settings", icon: Settings2, label: "Settings", action: () => { onOpenProfile(); setIsOpen(false); } },
    { id: "search", icon: Search, label: "Search Chats", action: () => { onOpenSearch(); setIsOpen(false); } },
    { id: "images", icon: ImagePlus, label: "Your Images & Creations", action: () => { onOpenArtifacts(); setIsOpen(false); } },
    { id: "projects", icon: FolderOpen, label: "Your Projects", action: () => { onOpenArtifacts(); setIsOpen(false); } },
    { id: "links", icon: Link2, label: "Link Library", action: () => { onOpenArtifacts(); setIsOpen(false); } },
    { id: "thread", icon: Sparkles, label: "New Thread", action: () => { onNewSession(); setIsOpen(false); } },
    { id: "token", icon: Copy, label: "Copy Session Token", action: copySessionToken },
  ];
  const popoverStyle = {
    position: "fixed",
    left: "calc(100vw - 344px)",
    right: "auto",
    top: 84,
    bottom: "auto",
    minWidth: 0,
    width: "min(320px, calc(100vw - 48px))",
    maxHeight: "calc(100vh - 120px)",
    zIndex: 60,
  };

  const popover = isOpen ? createPortal(
    <div className={`rail-account-sheet-popover ${isCollapsed ? "rail-account-sheet-popover-collapsed" : ""}`} data-testid="caos-rail-account-popover" style={popoverStyle}>
      <div className="rail-account-sheet" data-testid="caos-rail-account-sheet">
        <div className="rail-account-profile-card" data-testid="caos-rail-account-profile-card">
          <img alt={displayName || email || "User"} className="rail-account-profile-avatar" src={AVATAR_URL} />
          <strong data-testid="caos-rail-account-profile-name">{displayName}</strong>
          <span data-testid="caos-rail-account-profile-email">{email}</span>
          <span className="rail-account-role-chip" data-testid="caos-rail-account-role">Administrator</span>
        </div>

        <div className="rail-account-meta-grid" data-testid="caos-rail-account-meta-grid">
          <div className="rail-account-meta-card" data-testid="caos-rail-account-member-card"><span>Engine</span><strong>{engineLabel}</strong></div>
          <div className="rail-account-meta-card" data-testid="caos-rail-account-memory-card"><span>Permanent Memory</span><strong>On</strong></div>
          <div className="rail-account-meta-card" data-testid="caos-rail-account-conversation-card"><span>Remember Conversations</span><strong>On</strong></div>
        </div>

        <div className="rail-account-packet" data-testid="caos-rail-account-packet">
          <span data-testid="caos-rail-account-packet-label">ARC / WCW</span>
          <strong data-testid="caos-rail-account-packet-count">{wcwUsed || 0} / {wcwBudget || 200000}</strong>
          <div className="token-bar" data-testid="caos-rail-account-packet-bar">
            <div className="token-bar-fill" style={{ width: `${packetPercent}%` }} />
          </div>
          <div className="rail-account-packet-meta" data-testid="caos-rail-account-packet-meta">
            <span data-testid="caos-rail-account-prompt-tokens">Sent {wcwSent || 0}</span>
            <span data-testid="caos-rail-account-completion-tokens">Received {wcwReceived || 0}</span>
          </div>
        </div>

        <div className="rail-account-settings-list" data-testid="caos-rail-account-settings-list">
          {settingsItems.map((item) => (
            <button className="rail-account-setting-item" data-testid={`caos-rail-account-item-${item.id}`} key={item.id} onClick={item.action} type="button">
              <span><item.icon size={15} />{item.label}</span>
            </button>
          ))}
        </div>

        <button className="rail-account-item rail-account-item-muted" data-testid="caos-rail-account-item-logout" type="button">
          <span><LogOut size={15} />Log Out</span>
        </button>
        {menuStatus ? <div className="rail-account-status" data-testid="caos-rail-account-status">{menuStatus}</div> : null}
      </div>
    </div>,
    document.body,
  ) : null;

  return (
    <div className="rail-account-menu" data-testid="caos-rail-account-menu">
      <button className={`rail-user-card ${isCollapsed ? "rail-user-card-collapsed" : ""}`} data-testid="caos-rail-user-card" onClick={() => setIsOpen((value) => !value)}>
        <span className="rail-user-avatar" data-testid="caos-rail-user-avatar">
          <img alt={displayName || email || "User"} src={AVATAR_URL} />
        </span>
        {!isCollapsed ? (
          <span className="rail-account-trigger-copy">
            <strong data-testid="caos-rail-user-name">{displayName}</strong>
            <span data-testid="caos-rail-user-meta">{email}</span>
          </span>
        ) : null}
        {!isCollapsed ? <ChevronDown size={16} /> : null}
      </button>
      {popover}
    </div>
  );
};
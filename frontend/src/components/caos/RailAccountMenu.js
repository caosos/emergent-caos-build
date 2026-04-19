import { ChevronRight, Copy, FolderOpen, ImagePlus, Link2, LogOut, Search, Settings2, Sparkles, UserRound } from "lucide-react";
import { useMemo, useState } from "react";


const labelForProvider = (provider) => ({ openai: "ChatGPT", anthropic: "Claude", gemini: "Gemini", xai: "Grok" }[provider] || provider || "ChatGPT");


export const RailAccountMenu = ({ currentSessionId, displayName, email, isCollapsed, onNewSession, onOpenArtifacts, onOpenProfile, onOpenSearch, runtimeSettings, wcwBudget, wcwUsed, wcwSent, wcwReceived }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [activePanel, setActivePanel] = useState("desktop");
  const [menuStatus, setMenuStatus] = useState("");
  const engineLabel = useMemo(() => `${labelForProvider(runtimeSettings?.default_provider)} · ${runtimeSettings?.default_model || "gpt-5.2"}`, [runtimeSettings?.default_model, runtimeSettings?.default_provider]);
  const packetPercent = Math.min(100, Math.round(((wcwUsed || 0) / (wcwBudget || 1)) * 100));

  const copySessionToken = async () => {
    if (!currentSessionId) return setMenuStatus("Open a thread first to copy its token.");
    await navigator.clipboard.writeText(currentSessionId);
    setMenuStatus("Session token copied.");
  };

  const primaryItems = [
    { id: "desktop", icon: FolderOpen, label: "Desktop" },
    { id: "profile", icon: UserRound, label: "Profile", action: () => { onOpenProfile(); setIsOpen(false); } },
    { id: "search", icon: Search, label: "Search", action: () => { onOpenSearch(); setIsOpen(false); } },
    { id: "token", icon: Copy, label: "Session Token", action: copySessionToken },
    { id: "bootloader", icon: Sparkles, label: "Inject Bootloader", action: () => setMenuStatus("Bootloader controls will land in the operating-layer phase.") },
  ];
  const desktopItems = [
    { id: "files", icon: FolderOpen, label: "Files", action: onOpenArtifacts },
    { id: "photos", icon: ImagePlus, label: "Photos", action: onOpenArtifacts },
    { id: "links", icon: Link2, label: "Links", action: onOpenArtifacts },
    { id: "new-thread", icon: Sparkles, label: "New Thread", action: onNewSession },
  ];

  return (
    <div className="rail-account-menu" data-testid="caos-rail-account-menu">
      <button className={`rail-user-card ${isCollapsed ? "rail-user-card-collapsed" : ""}`} data-testid="caos-rail-user-card" onClick={() => setIsOpen((value) => !value)}>
        <span className="rail-user-avatar" data-testid="caos-rail-user-avatar">{(displayName || email || "U").trim().charAt(0).toUpperCase()}</span>
        {!isCollapsed ? (
          <span className="rail-account-trigger-copy">
            <strong data-testid="caos-rail-user-name">{displayName}</strong>
            <span data-testid="caos-rail-user-meta">{email}</span>
          </span>
        ) : null}
      </button>

      {isOpen ? (
        <div className={`rail-account-popover ${isCollapsed ? "rail-account-popover-collapsed" : ""}`} data-testid="caos-rail-account-popover">
          <div className="rail-account-primary" data-testid="caos-rail-account-primary-panel">
            {primaryItems.map((item) => (
              <button
                className={`rail-account-item ${activePanel === item.id ? "rail-account-item-active" : ""}`}
                data-testid={`caos-rail-account-item-${item.id}`}
                key={item.id}
                onClick={() => item.action ? item.action() : setActivePanel(item.id)}
                type="button"
              >
                <span><item.icon size={15} />{item.label}</span>
                {!item.action ? <ChevronRight size={14} /> : null}
              </button>
            ))}

            <div className="rail-account-engine" data-testid="caos-rail-account-engine">{engineLabel}</div>
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
            <button className="rail-account-item rail-account-item-muted" data-testid="caos-rail-account-item-logout" type="button">
              <span><LogOut size={15} />Log Out</span>
            </button>
          </div>

          {activePanel === "desktop" ? (
            <div className="rail-account-secondary" data-testid="caos-rail-account-secondary-panel">
              {desktopItems.map((item) => (
                <button className="rail-account-tile" data-testid={`caos-rail-account-tile-${item.id}`} key={item.id} onClick={() => { item.action(); setIsOpen(false); }} type="button">
                  <item.icon size={16} />
                  <span>{item.label}</span>
                </button>
              ))}
              <button className="rail-account-tile rail-account-tile-muted" data-testid="caos-rail-account-tile-settings" onClick={() => { onOpenProfile(); setIsOpen(false); }} type="button">
                <Settings2 size={16} />
                <span>Settings</span>
              </button>
            </div>
          ) : null}

          {menuStatus ? <div className="rail-account-status" data-testid="caos-rail-account-status">{menuStatus}</div> : null}
        </div>
      ) : null}
    </div>
  );
};
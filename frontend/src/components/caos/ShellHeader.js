import { useEffect, useState } from "react";
import { Menu, Plus, Search, Sparkles } from "lucide-react";


export const ShellHeader = ({ commitUserEmail, onNewSession, onOpenArtifacts, onOpenProfile, searchQuery, setSearchQuery, userEmail, wcwBudget, wcwUsed }) => {
  const [draftEmail, setDraftEmail] = useState(userEmail);
  const [menuOpen, setMenuOpen] = useState(false);
  const percent = Math.min(100, Math.round(((wcwUsed || 0) / (wcwBudget || 1)) * 100));

  useEffect(() => {
    setDraftEmail(userEmail);
  }, [userEmail]);

  const commitIfNeeded = () => commitUserEmail(draftEmail);

  return (
    <header className="caos-header" data-testid="caos-shell-header">
      <div className="caos-brand-block" data-testid="caos-brand-block">
        <button className="brand-chip" data-testid="caos-brand-chip">
          <Sparkles size={14} />
          <span>CAOS</span>
        </button>
        <div>
          <h1 data-testid="caos-header-title">Cognitive Adaptive Operating System</h1>
          <p data-testid="caos-header-subtitle">Continuous chat, context, continuity, and receipts.</p>
        </div>
      </div>

      <div className="caos-header-actions">
        <label className="inline-field" data-testid="caos-email-field">
          <span>User</span>
          <input
            data-testid="caos-user-email-input"
            value={draftEmail}
            onBlur={commitIfNeeded}
            onChange={(event) => setDraftEmail(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                event.preventDefault();
                commitIfNeeded();
              }
            }}
          />
        </label>

        <label className="inline-field search-field" data-testid="caos-search-field">
          <Search size={14} />
          <input
            data-testid="caos-thread-search-input"
            placeholder="Search this thread"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
          />
        </label>

        <div className="token-chip" data-testid="caos-token-meter">
          <span>{wcwUsed || 0} / {wcwBudget || 200000}</span>
          <div className="token-bar" data-testid="caos-token-meter-bar">
            <div className="token-bar-fill" style={{ width: `${percent}%` }} />
          </div>
        </div>

        <button className="primary-shell-button" data-testid="caos-new-session-button" onClick={onNewSession}>
          <Plus size={16} />
          <span>New Thread</span>
        </button>

        <div className="header-menu-wrap" data-testid="caos-header-menu-wrap">
          <button className="surface-button" data-testid="caos-header-menu-button" onClick={() => setMenuOpen((value) => !value)}>
            <Menu size={16} />
            <span>Menu</span>
          </button>
          {menuOpen ? (
            <div className="header-menu" data-testid="caos-header-menu">
              <button data-testid="caos-header-menu-new-thread" onClick={() => { setMenuOpen(false); onNewSession(); }}>New Thread</button>
              <button data-testid="caos-header-menu-profile" onClick={() => { setMenuOpen(false); onOpenProfile(); }}>Profile</button>
              <button data-testid="caos-header-menu-files" onClick={() => { setMenuOpen(false); onOpenArtifacts(); }}>Files & Artifacts</button>
            </div>
          ) : null}
        </div>
      </div>
    </header>
  );
};
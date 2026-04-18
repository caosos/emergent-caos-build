import { Plus, Search, Sparkles } from "lucide-react";


export const ShellHeader = ({ onNewSession, searchQuery, setSearchQuery, userEmail, setUserEmail, wcwBudget, wcwUsed }) => {
  const percent = Math.min(100, Math.round(((wcwUsed || 0) / (wcwBudget || 1)) * 100));

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
          <input data-testid="caos-user-email-input" value={userEmail} onChange={(event) => setUserEmail(event.target.value)} />
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
      </div>
    </header>
  );
};
import { Cpu, Search } from "lucide-react";


export const ShellHeader = ({ currentSession, searchQuery, setSearchQuery, wcwBudget, wcwUsed }) => {
  const percent = Math.min(100, Math.round(((wcwUsed || 0) / (wcwBudget || 1)) * 100));

  return (
    <header className="caos-header" data-testid="caos-shell-header">
      <div className="caos-header-context" data-testid="caos-header-context">
        <div>
          <h1 data-testid="caos-header-title">{currentSession?.title || "Chat"}</h1>
          <p data-testid="caos-header-subtitle">{currentSession?.session_id || "Start a thread from the left rail."}</p>
        </div>
      </div>

      <div className="caos-header-actions">
        <label className="inline-field search-field" data-testid="caos-search-field">
          <Search size={14} />
          <input
            data-testid="caos-thread-search-input"
            placeholder="Search this thread"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
          />
        </label>

        <div className="engine-chip" data-testid="caos-engine-chip">
          <Cpu size={14} />
          <span>OpenAI · GPT-5.2</span>
        </div>

        <div className="token-chip" data-testid="caos-token-meter">
          <span>{wcwUsed || 0} / {wcwBudget || 200000}</span>
          <div className="token-bar" data-testid="caos-token-meter-bar">
            <div className="token-bar-fill" style={{ width: `${percent}%` }} />
          </div>
        </div>
      </div>
    </header>
  );
};
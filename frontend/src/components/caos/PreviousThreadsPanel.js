import { Clock3, History, X } from "lucide-react";
import { useMemo, useState } from "react";


export const PreviousThreadsPanel = ({ currentSessionId, isOpen, onClose, onSelectSession, sessions }) => {
  const [query, setQuery] = useState("");
  const visibleSessions = useMemo(() => {
    if (!query.trim()) return sessions.slice(0, 16);
    const needle = query.toLowerCase();
    return sessions.filter((session) => `${session.title} ${session.last_message_preview || ""} ${session.lane || ""}`.toLowerCase().includes(needle)).slice(0, 16);
  }, [query, sessions]);

  if (!isOpen) return null;

  return (
    <aside className="previous-threads-panel" data-testid="caos-previous-threads-panel">
      <div className="previous-threads-header" data-testid="caos-previous-threads-header">
        <div className="context-card-heading">
          <History size={16} />
          <h2 data-testid="caos-previous-threads-title">Previous Threads</h2>
        </div>
        <button className="drawer-close-button" data-testid="caos-previous-threads-close-button" onClick={onClose} type="button">
          <X size={14} />
        </button>
      </div>

      <label className="previous-threads-search" data-testid="caos-previous-threads-search-row">
        <input
          data-testid="caos-previous-threads-search-input"
          placeholder="Filter previous threads"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>

      <div className="previous-threads-list" data-testid="caos-previous-threads-list">
        {visibleSessions.map((session) => (
          <button
            className={`previous-thread-card ${session.session_id === currentSessionId ? "previous-thread-card-active" : ""}`}
            data-testid={`caos-previous-thread-card-${session.session_id}`}
            key={session.session_id}
            onClick={() => {
              onSelectSession(session);
              onClose();
            }}
            type="button"
          >
            <div className="thread-card-topline">
              <strong data-testid={`caos-previous-thread-title-${session.session_id}`}>{session.title}</strong>
              <Clock3 size={14} />
            </div>
            <span className="thread-card-lane" data-testid={`caos-previous-thread-lane-${session.session_id}`}>Lane · {session.lane || "general"}</span>
            <span data-testid={`caos-previous-thread-preview-${session.session_id}`}>{session.last_message_preview || "No messages yet"}</span>
          </button>
        ))}
      </div>
    </aside>
  );
};
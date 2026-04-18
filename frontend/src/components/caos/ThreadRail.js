import { Clock3, MessageSquareText } from "lucide-react";


export const ThreadRail = ({ currentSessionId, onSelectSession, sessions }) => {
  return (
    <aside className="thread-rail" data-testid="caos-thread-rail">
      <div className="rail-header" data-testid="caos-thread-rail-header">
        <h2 data-testid="caos-thread-rail-title">Previous Threads</h2>
        <p data-testid="caos-thread-rail-count">{sessions.length} saved</p>
      </div>

      <div className="thread-list" data-testid="caos-thread-list">
        {sessions.length === 0 ? (
          <div className="thread-empty" data-testid="caos-thread-empty-state">
            <MessageSquareText size={18} />
            <span>No sessions yet</span>
          </div>
        ) : (
          sessions.map((session) => (
            <button
              className={`thread-card ${currentSessionId === session.session_id ? "thread-card-active" : ""}`}
              data-testid={`caos-thread-card-${session.session_id}`}
              key={session.session_id}
              onClick={() => onSelectSession(session)}
            >
              <div className="thread-card-topline">
                <strong data-testid={`caos-thread-title-${session.session_id}`}>{session.title}</strong>
                <Clock3 size={14} />
              </div>
              <span data-testid={`caos-thread-preview-${session.session_id}`}>
                {session.last_message_preview || "No messages yet"}
              </span>
            </button>
          ))
        )}
      </div>
    </aside>
  );
};
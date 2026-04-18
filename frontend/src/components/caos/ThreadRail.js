import { Clock3, FolderKanban, MessageSquareText, Sparkles, Wrench } from "lucide-react";


export const ThreadRail = ({ currentSessionId, onSelectSession, sessions }) => {
  return (
    <aside className="thread-rail" data-testid="caos-thread-rail">
      <div className="rail-brand" data-testid="caos-rail-brand">
        <div>
          <h2 data-testid="caos-thread-rail-title">CAOS</h2>
          <p data-testid="caos-thread-rail-subtitle">Cognitive Adaptive OS</p>
        </div>
      </div>

      <div className="rail-nav" data-testid="caos-rail-nav">
        <button className="rail-nav-primary" data-testid="caos-rail-new-chat-button">New Chat</button>
        <button className="rail-nav-item rail-nav-item-active" data-testid="caos-rail-chat-button">Chat</button>
        <button className="rail-nav-item" data-testid="caos-rail-create-button"><Sparkles size={14} />Create</button>
        <button className="rail-nav-item" data-testid="caos-rail-tools-button"><Wrench size={14} />Tools</button>
        <button className="rail-nav-item" data-testid="caos-rail-models-button"><Sparkles size={14} />Models</button>
        <button className="rail-nav-item" data-testid="caos-rail-projects-button"><FolderKanban size={14} />Projects</button>
        <button className="rail-nav-item" data-testid="caos-rail-threads-button"><MessageSquareText size={14} />Threads</button>
      </div>

      <div className="rail-header" data-testid="caos-thread-rail-header">
        <h2 data-testid="caos-thread-rail-recent-title">Recent</h2>
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

      <div className="rail-footer" data-testid="caos-rail-footer">
        <button className="rail-footer-button" data-testid="caos-rail-settings-button">Settings</button>
        <button className="rail-footer-button" data-testid="caos-rail-logout-button">Log Out</button>
      </div>
    </aside>
  );
};
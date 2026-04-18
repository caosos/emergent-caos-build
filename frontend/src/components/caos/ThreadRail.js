import { useMemo, useState } from "react";
import { Clock3, FolderKanban, MessageSquareText, PanelLeftOpen, Sparkles, Wrench } from "lucide-react";

import { RailAccountMenu } from "@/components/caos/RailAccountMenu";


export const ThreadRail = ({ currentSessionId, isCollapsed, onNewSession, onOpenArtifacts, onOpenProfile, onOpenSearch, onOpenThreads, onSelectSession, onToggleRail, profile, runtimeSettings, sessions, userEmail }) => {
  const displayName = profile?.preferred_name || userEmail?.split("@")[0] || "Michael";
  const [railSearch, setRailSearch] = useState("");
  const visibleSessions = useMemo(() => {
    if (!railSearch.trim()) return sessions;
    const query = railSearch.toLowerCase();
    return sessions.filter((session) => `${session.title} ${session.last_message_preview || ""}`.toLowerCase().includes(query));
  }, [railSearch, sessions]);
  const recentSessions = visibleSessions.slice(0, 6);

  if (isCollapsed) {
    return (
      <aside className="thread-rail thread-rail-collapsed" data-testid="caos-thread-rail">
        <button className="rail-toggle-button" data-testid="caos-thread-rail-expand-button" onClick={onToggleRail}>
          <PanelLeftOpen size={16} />
        </button>
        <button className="rail-nav-primary rail-icon-button" data-testid="caos-rail-new-chat-button" onClick={onNewSession}>+</button>
        <div className="rail-mini-thread-list" data-testid="caos-mini-thread-list">
          {recentSessions.map((session) => (
            <button
              className={`rail-mini-thread-button ${currentSessionId === session.session_id ? "thread-card-active" : ""}`}
              data-testid={`caos-mini-thread-card-${session.session_id}`}
              key={session.session_id}
              onClick={() => onSelectSession(session)}
              title={session.title}
            >
              {(session.title || "N").trim().charAt(0).toUpperCase()}
            </button>
          ))}
        </div>
        <RailAccountMenu
          currentSessionId={currentSessionId}
          displayName={displayName}
          email={userEmail}
          isCollapsed
          onNewSession={onNewSession}
          onOpenArtifacts={onOpenArtifacts}
          onOpenProfile={onOpenProfile}
          onOpenSearch={onOpenSearch}
          runtimeSettings={runtimeSettings}
        />
      </aside>
    );
  }

  return (
    <aside className="thread-rail" data-testid="caos-thread-rail">
      <div className="rail-topline" data-testid="caos-rail-topline">
        <div className="rail-brand" data-testid="caos-rail-brand">
          <div>
            <h2 data-testid="caos-thread-rail-title">CAOS</h2>
            <p data-testid="caos-thread-rail-subtitle">Cognitive Adaptive OS</p>
          </div>
        </div>
        <button className="rail-toggle-button" data-testid="caos-thread-rail-collapse-button" onClick={onToggleRail}>
          <PanelLeftOpen size={16} />
        </button>
      </div>

      <div className="rail-nav" data-testid="caos-rail-nav">
        <button className="rail-nav-primary" data-testid="caos-rail-new-chat-button" onClick={onNewSession}>New Chat</button>
        <label className="rail-search-field" data-testid="caos-rail-search-field">
          <input
            data-testid="caos-rail-search-input"
            placeholder="Search chats..."
            value={railSearch}
            onChange={(event) => setRailSearch(event.target.value)}
          />
        </label>
        <button className="rail-nav-item rail-nav-item-active" data-testid="caos-rail-chat-button">Chat</button>
        <button className="rail-nav-item" data-testid="caos-rail-create-button"><Sparkles size={14} />Create</button>
        <button className="rail-nav-item" data-testid="caos-rail-tools-button"><Wrench size={14} />Tools</button>
        <button className="rail-nav-item" data-testid="caos-rail-models-button"><Sparkles size={14} />Models</button>
        <button className="rail-nav-item" data-testid="caos-rail-projects-button"><FolderKanban size={14} />Projects</button>
        <button className="rail-nav-item" data-testid="caos-rail-threads-button" onClick={onOpenThreads}><MessageSquareText size={14} />Threads</button>
      </div>

      <div className="rail-header" data-testid="caos-thread-rail-header">
        <h2 data-testid="caos-thread-rail-recent-title">Recent</h2>
        <p data-testid="caos-thread-rail-count">Showing {recentSessions.length} of {sessions.length}</p>
      </div>

      <div className="thread-list" data-testid="caos-thread-list">
        {recentSessions.length === 0 ? (
          <div className="thread-empty" data-testid="caos-thread-empty-state">
            <MessageSquareText size={18} />
            <span>No sessions yet</span>
          </div>
        ) : (
          recentSessions.map((session) => (
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
              <span className="thread-card-lane" data-testid={`caos-thread-lane-${session.session_id}`}>
                Lane · {session.lane || "general"}
              </span>
              <span data-testid={`caos-thread-preview-${session.session_id}`}>
                {session.last_message_preview || "No messages yet"}
              </span>
            </button>
          ))
        )}
      </div>

      <div className="rail-footer" data-testid="caos-rail-footer">
        <RailAccountMenu
          currentSessionId={currentSessionId}
          displayName={displayName}
          email={userEmail}
          isCollapsed={false}
          onNewSession={onNewSession}
          onOpenArtifacts={onOpenArtifacts}
          onOpenProfile={onOpenProfile}
          onOpenSearch={onOpenSearch}
          runtimeSettings={runtimeSettings}
        />
      </div>
    </aside>
  );
};
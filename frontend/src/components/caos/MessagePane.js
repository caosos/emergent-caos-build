const formatRole = (role) => (role === "assistant" ? "CAOS" : role === "user" ? "You" : "System");


export const MessagePane = ({ busy, currentSession, messages }) => {
  return (
    <section className="message-pane" data-testid="caos-message-pane">
      <div className="message-pane-header" data-testid="caos-message-pane-header">
        <div>
          <h2 data-testid="caos-current-thread-title">{currentSession?.title || "No active thread"}</h2>
          <p data-testid="caos-current-thread-id">{currentSession?.session_id || "Create a thread to begin."}</p>
        </div>
        {busy ? <span className="busy-chip" data-testid="caos-busy-chip">Thinking…</span> : null}
      </div>

      <div className="message-scroll" data-testid="caos-message-scroll">
        {messages.length === 0 ? (
          <div className="message-empty" data-testid="caos-message-empty-state">
            <h3 data-testid="caos-message-empty-title">The real shell is live.</h3>
            <p data-testid="caos-message-empty-text">
              Start a thread and send a message. The backend will sanitize the session, retrieve relevant memory, and return a session-scoped reply.
            </p>
          </div>
        ) : (
          messages.map((message) => (
            <article
              className={`message-bubble message-bubble-${message.role}`}
              data-testid={`caos-message-bubble-${message.id}`}
              key={message.id}
            >
              <div className="message-bubble-topline">
                <strong data-testid={`caos-message-role-${message.id}`}>{formatRole(message.role)}</strong>
                <span data-testid={`caos-message-time-${message.id}`}>{new Date(message.timestamp).toLocaleString()}</span>
              </div>
              <p data-testid={`caos-message-content-${message.id}`}>{message.content}</p>
            </article>
          ))
        )}
      </div>
    </section>
  );
};
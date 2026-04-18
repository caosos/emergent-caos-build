import { Copy, CornerDownLeft, Receipt, ThumbsUp, Volume2 } from "lucide-react";
import { useState } from "react";


const formatRole = (role) => (role === "assistant" ? "CAOS" : role === "user" ? "You" : "System");


export const MessagePane = ({ busy, currentSession, messages, onSpeak, receipts }) => {
  const [actionStatus, setActionStatus] = useState("");
  const [messageMeta, setMessageMeta] = useState({});
  const [speakingId, setSpeakingId] = useState("");

  const updateMeta = (messageId, updater) => {
    setMessageMeta((previous) => ({
      ...previous,
      [messageId]: updater(previous[messageId] || { reactions: [], replies: [], replyDraft: "", showReceipt: false, showReply: false }),
    }));
  };

  const handleCopy = async (message) => {
    try {
      await navigator.clipboard.writeText(message.content);
      setActionStatus("Message copied.");
    } catch {
      setActionStatus("Clipboard permission was denied.");
    }
  };

  const handleReadAloud = async (message) => {
    try {
      if (speakingId === message.id) {
        setSpeakingId("");
        setActionStatus("Read aloud stopped.");
        return;
      }
      setSpeakingId(message.id);
      setActionStatus("Read aloud started.");
      await onSpeak(message.content);
      setSpeakingId("");
    } catch {
      setSpeakingId("");
      setActionStatus("Read aloud is unavailable in this browser.");
    }
  };

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
          messages.map((message) => {
            const meta = messageMeta[message.id] || { reactions: [], replies: [], replyDraft: "", showReceipt: false, showReply: false };
            const linkedReceipt = receipts.find((receipt) => receipt.assistant_message_id === message.id);

            return (
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
                <div className="message-actions-row" data-testid={`caos-message-actions-${message.id}`}>
                  <button className="message-action-button" data-testid={`caos-message-copy-${message.id}`} onClick={() => handleCopy(message)}>
                    <Copy size={14} />
                    <span>Copy</span>
                  </button>
                  {message.role === "assistant" ? (
                    <button className="message-action-button" data-testid={`caos-message-read-${message.id}`} onClick={() => handleReadAloud(message)}>
                      <Volume2 size={14} />
                      <span>{speakingId === message.id ? "Stop" : "Read"}</span>
                    </button>
                  ) : null}
                  <button
                    className="message-action-button"
                    data-testid={`caos-message-reply-${message.id}`}
                    onClick={() => updateMeta(message.id, (state) => ({ ...state, showReply: !state.showReply }))}
                  >
                    <CornerDownLeft size={14} />
                    <span>Reply</span>
                  </button>
                  <button
                    className="message-action-button"
                    data-testid={`caos-message-react-${message.id}`}
                    onClick={() => updateMeta(message.id, (state) => ({ ...state, reactions: state.reactions.includes("Useful") ? state.reactions : [...state.reactions, "Useful"] }))}
                  >
                    <ThumbsUp size={14} />
                    <span>Useful</span>
                  </button>
                  {linkedReceipt ? (
                    <button
                      className="message-action-button"
                      data-testid={`caos-message-receipt-${message.id}`}
                      onClick={() => updateMeta(message.id, (state) => ({ ...state, showReceipt: !state.showReceipt }))}
                    >
                      <Receipt size={14} />
                      <span>Receipt</span>
                    </button>
                  ) : null}
                </div>

                {meta.reactions.length ? (
                  <div className="reaction-row" data-testid={`caos-message-reaction-row-${message.id}`}>
                    {meta.reactions.map((reaction) => (
                      <span className="reaction-chip" data-testid={`caos-message-reaction-${message.id}-${reaction}`} key={reaction}>{reaction}</span>
                    ))}
                  </div>
                ) : null}

                {meta.showReply ? (
                  <div className="reply-shell" data-testid={`caos-message-reply-shell-${message.id}`}>
                    <textarea
                      data-testid={`caos-message-reply-input-${message.id}`}
                      placeholder="Add a quick inline reply"
                      rows={2}
                      value={meta.replyDraft}
                      onChange={(event) => updateMeta(message.id, (state) => ({ ...state, replyDraft: event.target.value }))}
                    />
                    <button
                      className="message-action-button"
                      data-testid={`caos-message-reply-save-${message.id}`}
                      onClick={() => updateMeta(message.id, (state) => ({
                        ...state,
                        replies: state.replyDraft.trim() ? [...state.replies, state.replyDraft.trim()] : state.replies,
                        replyDraft: "",
                      }))}
                    >
                      Save reply
                    </button>
                    {meta.replies.map((reply, index) => (
                      <div className="reply-card" data-testid={`caos-message-reply-card-${message.id}-${index}`} key={`${message.id}-${index}`}>{reply}</div>
                    ))}
                  </div>
                ) : null}

                {meta.showReceipt && linkedReceipt ? (
                  <div className="receipt-inline" data-testid={`caos-message-inline-receipt-${message.id}`}>
                    <strong>Receipt lineage {linkedReceipt.lineage_depth}</strong>
                    <span>Terms: {linkedReceipt.retrieval_terms.join(", ") || "none"}</span>
                    <span>Reduction: {Math.round((linkedReceipt.reduction_ratio || 0) * 100)}%</span>
                  </div>
                ) : null}
              </article>
            );
          })
        )}
      </div>
      {actionStatus ? <div className="message-action-status" data-testid="caos-message-action-status">{actionStatus}</div> : null}
    </section>
  );
};
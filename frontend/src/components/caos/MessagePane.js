import { Copy, CornerDownLeft, FileSearch, ThumbsUp, Volume2 } from "lucide-react";
import { useRef, useState } from "react";

import { LatencyIndicator } from "@/components/caos/LatencyIndicator";
import { MultiAgentMessageGroup } from "@/components/caos/MultiAgentMessageGroup";
import { SelectionReactionPopover } from "@/components/caos/SelectionReactionPopover";


const formatRole = (role) => (role === "assistant" ? "CAOS" : role === "user" ? "You" : "System");
const formatTimestamp = (value) => new Date(value).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });


export const MessagePane = ({ busy, currentSession, messages, onSpeak, receipts }) => {
  const [actionStatus, setActionStatus] = useState("");
  const [messageMeta, setMessageMeta] = useState({});
  const [speakingId, setSpeakingId] = useState("");
  const scrollRef = useRef(null);

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
      <div className="message-scroll" data-testid="caos-message-scroll" ref={scrollRef}>
        <SelectionReactionPopover
          containerRef={scrollRef}
          onCopy={async (text) => {
            try { await navigator.clipboard.writeText(text); setActionStatus("Copied highlighted text."); }
            catch { setActionStatus("Clipboard permission denied."); }
          }}
          onReact={(emoji) => setActionStatus(`Reacted ${emoji} to selection.`)}
          onReadAloud={async (text) => { try { await onSpeak(text); } catch { setActionStatus("Read aloud unavailable."); } }}
          onReply={(text) => setActionStatus(`Reply to: "${text.slice(0, 48)}${text.length > 48 ? "…" : ""}"`)}
        />
        {busy ? <span className="busy-chip message-pane-busy-chip" data-testid="caos-busy-chip">Thinking…</span> : null}
        {messages.length === 0 ? (
          <div className="message-empty" data-testid="caos-message-empty-state">
            <h3 data-testid="caos-message-empty-title">What would you like to do?</h3>
            <p data-testid="caos-message-empty-text">
              Ask anything. Create. Analyze. Build. All in one workspace.
            </p>
          </div>
        ) : (
          messages.map((message) => {
            if (message.multi_agent) {
              return (
                <MultiAgentMessageGroup
                  agents={message.agents}
                  synthesis={message.synthesis}
                  key={message.id}
                  onSpeak={onSpeak}
                  timestamp={message.timestamp}
                />
              );
            }
            const meta = messageMeta[message.id] || { reactions: [], replies: [], replyDraft: "", showReceipt: false, showReply: false };
            const linkedReceipt = receipts.find((receipt) => receipt.assistant_message_id === message.id);
            const isPending = message.pending === true;
            const isStreamingPlaceholder = message.role === "assistant" && isPending && !message.content;

            return (
              <article
                className={`message-bubble message-bubble-${message.role} ${isPending ? "message-bubble-pending" : ""}`}
                data-testid={`caos-message-bubble-${message.id}`}
                key={message.id}
              >
                <div className="message-bubble-topline">
                  <strong data-testid={`caos-message-role-${message.id}`}>{formatRole(message.role)}</strong>
                  <span data-testid={`caos-message-time-${message.id}`}>{formatTimestamp(message.timestamp)}</span>
                  {message.role === "assistant" && linkedReceipt ? (
                    <LatencyIndicator receipt={linkedReceipt} />
                  ) : null}
                </div>
                {isStreamingPlaceholder ? (
                  <div className="typing-indicator" data-testid={`caos-typing-indicator-${message.id}`}>
                    <span /><span /><span />
                  </div>
                ) : (
                  <p data-testid={`caos-message-content-${message.id}`}>
                    {message.content}
                    {isPending && message.role === "assistant" && message.content ? (
                      <span className="streaming-cursor" data-testid={`caos-streaming-cursor-${message.id}`}>▌</span>
                    ) : null}
                  </p>
                )}
                {isPending ? null : (
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
                      <FileSearch size={14} />
                      <span>Context</span>
                    </button>
                  ) : null}
                </div>
                )}

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
                    <strong>Context Diagnostics · lineage {linkedReceipt.lineage_depth}</strong>
                    <span>Runtime: {linkedReceipt.provider} · {linkedReceipt.model}</span>
                    <span>Terms: {linkedReceipt.retrieval_terms.join(", ") || "none"}</span>
                    <span>Bins: {linkedReceipt.subject_bins?.join(", ") || "none"}</span>
                    <span>Continuity packets: {(linkedReceipt.selected_summary_ids?.length || 0) + (linkedReceipt.selected_seed_ids?.length || 0)}</span>
                    <span>Reduction: {Math.round((linkedReceipt.reduction_ratio || 0) * 100)}%</span>
                    <span>Kept/Dropped/Compressed/Trimmed: {linkedReceipt.retained_message_count || 0}/{linkedReceipt.dropped_message_count || 0}/{linkedReceipt.compressed_message_count || 0}/{linkedReceipt.budget_trimmed_count || 0}</span>
                    <span>Global cache: {linkedReceipt.global_cache_count || 0} ({linkedReceipt.global_bin_status || "empty"})</span>
                    <span>{linkedReceipt.retention_explanation?.[0] || "Retention reasoning pending."}</span>
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
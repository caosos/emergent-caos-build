import { ArrowDown, Clock, Copy, CornerDownLeft, FileSearch, Mail, Paperclip, ThumbsUp, Volume2, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";

import { LatencyIndicator } from "@/components/caos/LatencyIndicator";
import { MultiAgentMessageGroup } from "@/components/caos/MultiAgentMessageGroup";
import { SelectionReactionPopover } from "@/components/caos/SelectionReactionPopover";


const formatRole = (role) => (role === "assistant" ? "CAOS" : role === "user" ? "MY" : "System");
const formatTimestamp = (value) => new Date(value).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
const formatFullDate = (value) => {
  try {
    const d = new Date(value);
    return `${d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })} · ${d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`;
  } catch { return ""; }
};

const ATTACH_WINDOW_MS = 75 * 1000;  // files uploaded within 75s of a user message = attached to that message


export const MessagePane = ({ busy, currentSession, files, messages, onSpeak, receipts }) => {
  const [actionStatus, setActionStatus] = useState("");
  const [messageMeta, setMessageMeta] = useState({});
  const [speakingId, setSpeakingId] = useState("");
  const [lightboxImage, setLightboxImage] = useState(null);
  const [showScrollBottom, setShowScrollBottom] = useState(false);
  const scrollRef = useRef(null);
  const sessionScrollRef = useRef("");
  const [portalReady, setPortalReady] = useState(false);

  useEffect(() => {
    setPortalReady(true);
  }, []);

  const resolveScrollTarget = () => {
    const container = scrollRef.current;
    if (!container) return { mode: "window", node: document.scrollingElement || document.documentElement };
    const style = window.getComputedStyle(container);
    const usesInternalScroll = ["auto", "scroll", "overlay"].includes(style.overflowY) && container.scrollHeight > container.clientHeight + 4;
    const body = document.body;
    const root = document.scrollingElement || document.documentElement;
    const bodyScrollHeight = body?.scrollHeight || 0;
    const rootScrollHeight = root?.scrollHeight || 0;
    const pageNode = bodyScrollHeight > rootScrollHeight ? body : root;
    return usesInternalScroll
      ? { mode: "container", node: container }
      : { mode: "window", node: pageNode };
  };

  const getScrollMetrics = () => {
    const target = resolveScrollTarget();
    const scrolled = target.mode === "container"
      ? target.node.scrollTop
      : (window.scrollY || document.documentElement.scrollTop || target.node.scrollTop || 0);
    const viewport = target.mode === "container" ? target.node.clientHeight : window.innerHeight;
    const height = target.node.scrollHeight - viewport;
    const remaining = height - scrolled;
    return { remaining, scrolled, target };
  };

  // Track window scroll position to decide whether to show the jump-to-bottom FAB.
  useEffect(() => {
    const handler = () => {
      const { remaining } = getScrollMetrics();
      setShowScrollBottom((prev) => (prev ? remaining > 120 : remaining > 260));
    };
    const target = resolveScrollTarget();
    const listenerNode = target.mode === "container" ? target.node : window;
    listenerNode?.addEventListener("scroll", handler, { passive: true });
    handler();
    return () => listenerNode?.removeEventListener("scroll", handler);
  }, [messages.length]);

  const scrollToBottom = (behavior = "smooth") => {
    try {
      const target = resolveScrollTarget();
      if (target.mode === "container") {
        if (behavior === "auto") target.node.scrollTop = target.node.scrollHeight;
        else target.node.scrollTo({ top: target.node.scrollHeight, behavior });
        return;
      }
      window.scrollTo({ top: target.node.scrollHeight, behavior });
    } catch { /* no-op */ }
  };

  const snapToBottom = () => scrollToBottom("auto");

  useEffect(() => {
    const sessionId = currentSession?.session_id || "";
    const sessionChanged = sessionScrollRef.current !== sessionId;
    sessionScrollRef.current = sessionId;
    if (!messages.length) return undefined;
    const { remaining } = getScrollMetrics();
    const shouldAutoScroll = sessionChanged || busy || remaining < 180;
    if (!shouldAutoScroll) return undefined;
    let cancelled = false;
    const cancel = () => { cancelled = true; };
    const run = () => {
      if (cancelled) return;
      snapToBottom();
    };
    run();
    const timers = [80, 220, 520].map((delay) => window.setTimeout(run, delay));
    const observerNode = scrollRef.current;
    const resizeObserver = typeof ResizeObserver !== "undefined" && observerNode
      ? new ResizeObserver(() => run())
      : null;
    resizeObserver?.observe(observerNode);
    const cleanupNode = resolveScrollTarget().mode === "container" ? resolveScrollTarget().node : window;
    cleanupNode?.addEventListener("wheel", cancel, { passive: true });
    cleanupNode?.addEventListener("touchmove", cancel, { passive: true });
    return () => {
      timers.forEach((timer) => window.clearTimeout(timer));
      resizeObserver?.disconnect();
      cleanupNode?.removeEventListener("wheel", cancel);
      cleanupNode?.removeEventListener("touchmove", cancel);
    };
  }, [busy, currentSession?.session_id, messages.length, receipts.length, files.length]);

  // Close lightbox on Escape
  useEffect(() => {
    if (!lightboxImage) return undefined;
    const esc = (event) => { if (event.key === "Escape") setLightboxImage(null); };
    document.addEventListener("keydown", esc);
    return () => document.removeEventListener("keydown", esc);
  }, [lightboxImage]);

  // Auto-clear transient status after 4s so stale banners never linger.
  useEffect(() => {
    if (!actionStatus) return undefined;
    const timer = setTimeout(() => setActionStatus(""), 4000);
    return () => clearTimeout(timer);
  }, [actionStatus]);

  // Map each user message → list of files uploaded within ATTACH_WINDOW_MS
  // of that message's timestamp. Base44-parity: photos show INLINE on the
  // bubble instead of silently attaching.
  const userMessageAttachments = useMemo(() => {
    const bySession = (files || []).filter((file) => file.session_id === currentSession?.session_id);
    if (bySession.length === 0) return {};
    const map = {};
    for (const message of messages) {
      if (message.role !== "user" || !message.timestamp) continue;
      const anchor = new Date(message.timestamp).getTime();
      map[message.id] = bySession.filter((file) => {
        const uploaded = new Date(file.created_at).getTime();
        return Math.abs(uploaded - anchor) < ATTACH_WINDOW_MS;
      });
    }
    return map;
  }, [files, messages, currentSession?.session_id]);

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
    } catch (error) {
      setSpeakingId("");
      setActionStatus(`Read aloud failed: ${(error?.message || "unknown").slice(0, 120)}`);
    }
  };

  const handleEmail = (message) => {
    try {
      const subject = currentSession?.title?.trim() || "Draft from CAOS";
      const body = message.content?.trim() || "";
      window.location.href = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
      setActionStatus("Opening your email app.");
    } catch {
      setActionStatus("Email compose could not be opened.");
    }
  };

  const scrollButton = (
    <button
      aria-label="Last message"
      className="scroll-to-bottom-button"
      data-testid="caos-scroll-to-bottom-button"
      onClick={(event) => {
        scrollToBottom();
        event.currentTarget.blur();
      }}
      title="Last message"
      type="button"
    >
      <ArrowDown size={16} />
    </button>
  );

  return (
    <section className="message-pane" data-testid="caos-message-pane">
      <div
        aria-hidden="true"
        className="message-pane-header-curtain"
        data-testid="caos-message-header-curtain"
      />
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
                  sessionTitle={currentSession?.title}
                  timestamp={message.timestamp}
                />
              );
            }
            const meta = messageMeta[message.id] || { reactions: [], replies: [], replyDraft: "", showReceipt: false, showReply: false };
            const linkedReceipt = receipts.find((receipt) => receipt.assistant_message_id === message.id);
            const isPending = message.pending === true;
            const isFailed = message.failed === true;
            const isStreamingPlaceholder = message.role === "assistant" && isPending && !message.content;

            return (
              <article
                className={`message-bubble message-bubble-${message.role} ${isPending ? "message-bubble-pending" : ""} ${isFailed ? "message-bubble-failed" : ""}`}
                data-testid={`caos-message-bubble-${message.id}`}
                key={message.id}
              >
                <div className="message-bubble-topline">
                  <strong data-testid={`caos-message-role-${message.id}`}>{formatRole(message.role)}</strong>
                  <span data-testid={`caos-message-time-${message.id}`}>{formatTimestamp(message.timestamp)}</span>
                  {isFailed ? <span className="message-failed-chip" data-testid={`caos-message-failed-chip-${message.id}`}>Issue</span> : null}
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
                {message.error ? <div className="message-error-note" data-testid={`caos-message-error-${message.id}`}>{message.error}</div> : null}
                {message.role === "user" && (userMessageAttachments[message.id]?.length || 0) > 0 ? (
                  <div className="message-attachments" data-testid={`caos-message-attachments-${message.id}`}>
                    {userMessageAttachments[message.id].map((file) => {
                      const isImage = (file.mime_type || "").startsWith("image/") && !!file.url;
                      return isImage ? (
                        <button
                          className="message-attachment-image"
                          data-testid={`caos-message-attachment-image-${file.id}`}
                          key={file.id}
                          onClick={() => setLightboxImage({ url: file.url, name: file.name })}
                          title="Click to expand"
                          type="button"
                        >
                          <img alt={file.name} loading="lazy" src={file.url} />
                        </button>
                      ) : (
                        <a
                          className="message-attachment-chip"
                          data-testid={`caos-message-attachment-chip-${file.id}`}
                          href={file.url || "#"}
                          key={file.id}
                          rel="noopener noreferrer"
                          target="_blank"
                          title={file.name}
                        >
                          <Paperclip size={12} />
                          <span>{file.name}</span>
                        </a>
                      );
                    })}
                  </div>
                ) : null}
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
                  {message.role === "assistant" && message.content ? (
                    <button className="message-action-button" data-testid={`caos-message-email-${message.id}`} onClick={() => handleEmail(message)}>
                      <Mail size={14} />
                      <span>Mail</span>
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

                {isPending ? null : (
                  <div className="message-footer" data-testid={`caos-message-footer-${message.id}`}>
                    <span data-testid={`caos-message-fulldate-${message.id}`}>{formatFullDate(message.timestamp)}</span>
                    {message.role === "assistant" && (linkedReceipt?.latency_ms || message.latency_ms) ? (
                      <span className="message-footer-latency-chip" data-testid={`caos-message-latency-${message.id}`} title="Response latency">
                        <Clock size={11} />
                        <strong>{(((linkedReceipt?.latency_ms || message.latency_ms) || 0) / 1000).toFixed(1)}s</strong>
                      </span>
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
      {showScrollBottom ? (portalReady ? createPortal(scrollButton, document.body) : scrollButton) : null}
      {lightboxImage ? (
        <div
          className="image-lightbox-backdrop"
          data-testid="caos-image-lightbox-backdrop"
          onClick={() => setLightboxImage(null)}
        >
          <button
            aria-label="Close image"
            className="image-lightbox-close"
            data-testid="caos-image-lightbox-close"
            onClick={(event) => { event.stopPropagation(); setLightboxImage(null); }}
            type="button"
          >
            <X size={18} />
          </button>
          <div className="image-lightbox-inner" onClick={(event) => event.stopPropagation()}>
            <img alt={lightboxImage.name} data-testid="caos-image-lightbox-image" src={lightboxImage.url} />
          </div>
        </div>
      ) : null}
    </section>
  );
};
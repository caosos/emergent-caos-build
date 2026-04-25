import { Check, Flag, History, Pencil, Trash2, X } from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";

import { ThreadMiniMeter } from "@/components/caos/ThreadMiniMeter";


const estimateSessionTokens = (session) => {
  const previewLen = String(session?.last_message_preview || "").length;
  const baseline = Math.max(0, session?.message_count || 0) * 180;
  return Math.ceil((previewLen * 4 + baseline) / 4);
};

/**
 * Base44-parity: renders INLINE inside the left rail (not as an overlay).
 * Each thread card exposes inline rename / flag / delete actions on hover,
 * plus a mini-WCW meter. Matches UX_BLUEPRINT §D precisely.
 */
export const PreviousThreadsPanel = ({
  currentSessionId,
  isEmbedded = false,
  isOpen,
  onClose,
  onDeleteSession,
  onFlagSession,
  onRenameSession,
  onSelectSession,
  sessions,
  wcwBudget = 200000,
  wcwUsed = 0,
  provider,
}) => {
  const [query, setQuery] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editTitle, setEditTitle] = useState("");
  const [confirmDeleteId, setConfirmDeleteId] = useState(null);
  const panelRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return undefined;
    const handler = (event) => {
      if (panelRef.current && !panelRef.current.contains(event.target)) {
        onClose?.();
      }
    };
    const escHandler = (event) => { if (event.key === "Escape") onClose?.(); };
    // Small timeout so the click that opened the panel doesn't immediately close it
    const t = setTimeout(() => document.addEventListener("mousedown", handler), 100);
    document.addEventListener("keydown", escHandler);
    return () => {
      clearTimeout(t);
      document.removeEventListener("mousedown", handler);
      document.removeEventListener("keydown", escHandler);
    };
  }, [isOpen, onClose]);

  const visibleSessions = useMemo(() => {
    if (!query.trim()) return sessions.slice(0, 40);
    const needle = query.toLowerCase();
    return sessions.filter((s) => `${s.title} ${s.last_message_preview || ""} ${s.lane || ""}`.toLowerCase().includes(needle)).slice(0, 40);
  }, [query, sessions]);

  if (!isOpen) return null;

  const beginRename = (session) => {
    setEditingId(session.session_id);
    setEditTitle(session.title || "");
    setConfirmDeleteId(null);
  };

  const commitRename = async (session) => {
    const next = editTitle.trim();
    if (next && next !== session.title) {
      await onRenameSession?.(session.session_id, next);
    }
    setEditingId(null);
    setEditTitle("");
  };

  const cancelRename = () => {
    setEditingId(null);
    setEditTitle("");
  };

  return (
    <aside
      className={`previous-threads-panel ${isEmbedded ? "previous-threads-panel-embedded" : ""}`}
      data-testid="caos-previous-threads-panel"
      ref={panelRef}
    >
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
          placeholder="Search across all threads…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>

      <div className="previous-threads-list" data-testid="caos-previous-threads-list">
        {visibleSessions.length === 0 ? (
          <div className="thread-empty" data-testid="caos-previous-threads-empty">No threads yet</div>
        ) : null}
        {visibleSessions.map((session) => {
          const isActive = session.session_id === currentSessionId;
          const isEditing = editingId === session.session_id;
          const awaitingDelete = confirmDeleteId === session.session_id;
          const tokens = isActive ? (wcwUsed || estimateSessionTokens(session)) : estimateSessionTokens(session);
          return (
            <div
              className={`previous-thread-card ${isActive ? "previous-thread-card-active" : ""} ${session.is_flagged ? "previous-thread-card-flagged" : ""}`}
              data-testid={`caos-previous-thread-card-${session.session_id}`}
              key={session.session_id}
            >
              <button
                className="previous-thread-card-body"
                data-testid={`caos-previous-thread-select-${session.session_id}`}
                disabled={isEditing}
                onClick={() => { onSelectSession(session); onClose?.(); }}
                type="button"
              >
                <div className="thread-card-topline">
                  {isEditing ? (
                    <input
                      autoFocus
                      className="previous-thread-rename-input"
                      data-testid={`caos-previous-thread-rename-input-${session.session_id}`}
                      onBlur={() => commitRename(session)}
                      onClick={(event) => event.stopPropagation()}
                      onChange={(event) => setEditTitle(event.target.value)}
                      onKeyDown={(event) => {
                        event.stopPropagation();
                        if (event.key === "Enter") commitRename(session);
                        if (event.key === "Escape") cancelRename();
                      }}
                      value={editTitle}
                    />
                  ) : (
                    <strong data-testid={`caos-previous-thread-title-${session.session_id}`}>{session.title}</strong>
                  )}
                  {session.is_flagged ? (
                    <Flag size={12} className="previous-thread-flag-icon" data-testid={`caos-previous-thread-flag-${session.session_id}`} />
                  ) : null}
                </div>
                <span data-testid={`caos-previous-thread-preview-${session.session_id}`}>
                  {session.last_message_preview || "No messages yet"}
                </span>
                <ThreadMiniMeter
                  budget={wcwBudget}
                  isEstimate={!isActive}
                  provider={provider}
                  testId={`caos-previous-thread-meter-${session.session_id}`}
                  tokens={tokens}
                />
              </button>
              {!isActive ? (
                <span className="previous-thread-meter-hint" data-testid={`caos-previous-thread-meter-hint-${session.session_id}`}>
                  — open thread to load meter
                </span>
              ) : null}
              <div className="previous-thread-card-actions" data-testid={`caos-previous-thread-actions-${session.session_id}`}>
                {awaitingDelete ? (
                  <>
                    <button
                      aria-label="Confirm delete"
                      className="previous-thread-action-btn previous-thread-action-confirm"
                      data-testid={`caos-previous-thread-confirm-delete-${session.session_id}`}
                      onClick={async () => {
                        await onDeleteSession?.(session.session_id);
                        setConfirmDeleteId(null);
                      }}
                      type="button"
                    >
                      <Check size={12} />
                    </button>
                    <button
                      aria-label="Cancel delete"
                      className="previous-thread-action-btn"
                      data-testid={`caos-previous-thread-cancel-delete-${session.session_id}`}
                      onClick={() => setConfirmDeleteId(null)}
                      type="button"
                    >
                      <X size={12} />
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      aria-label="Rename thread"
                      className="previous-thread-action-btn previous-thread-action-rename"
                      data-testid={`caos-previous-thread-rename-${session.session_id}`}
                      onClick={() => beginRename(session)}
                      title="Rename thread"
                      type="button"
                    >
                      <Pencil size={12} />
                    </button>
                    <button
                      aria-label="Toggle flag"
                      className={`previous-thread-action-btn previous-thread-action-flag ${session.is_flagged ? "previous-thread-action-flag-active" : ""}`}
                      data-testid={`caos-previous-thread-toggle-flag-${session.session_id}`}
                      onClick={() => onFlagSession?.(session)}
                      title={session.is_flagged ? "Unflag thread" : "Flag for follow-up"}
                      type="button"
                    >
                      <Flag size={12} />
                    </button>
                    <button
                      aria-label="Delete thread"
                      className="previous-thread-action-btn previous-thread-action-delete"
                      data-testid={`caos-previous-thread-delete-${session.session_id}`}
                      onClick={() => setConfirmDeleteId(session.session_id)}
                      title="Delete thread"
                      type="button"
                    >
                      <Trash2 size={12} />
                    </button>
                  </>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </aside>
  );
};

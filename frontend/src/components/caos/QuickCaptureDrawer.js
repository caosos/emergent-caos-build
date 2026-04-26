import axios from "axios";
import {
  ArrowUpRight,
  Copy,
  Inbox,
  Key,
  RefreshCw,
  Send,
  StickyNote,
  Trash2,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";

import { API } from "@/config/apiBase";

/**
 * Quick Capture Drawer — voice/text dump-and-go inbox.
 *
 * Sticky-note view of every capture (manual / shortcut / pendant / api),
 * promote-to-chat button on each card, manual entry textarea at the top,
 * and a Settings panel for the per-user API key (shown ONCE on rotation).
 */

const SOURCE_PILLS = {
  manual:      { label: "MANUAL",   className: "capture-source-manual" },
  shortcut:    { label: "SHORTCUT", className: "capture-source-shortcut" },
  bee_pendant: { label: "BEE",      className: "capture-source-bee" },
  api:         { label: "API",      className: "capture-source-api" },
  voice:       { label: "VOICE",    className: "capture-source-voice" },
};

const formatRelative = (iso) => {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    const diff = (Date.now() - d.getTime()) / 1000;
    if (diff < 60) return "just now";
    if (diff < 3600) return `${Math.round(diff / 60)} min ago`;
    if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
    return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch { return "—"; }
};

export const QuickCaptureDrawer = ({ isOpen, onClose, userEmail, onPromoted }) => {
  const [captures, setCaptures] = useState([]);
  const [counts, setCounts] = useState({ new: 0, promoted: 0, dismissed: 0 });
  const [filter, setFilter] = useState("new"); // new | promoted | dismissed | all
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  // API key state
  const [showKeyPanel, setShowKeyPanel] = useState(false);
  const [keyMeta, setKeyMeta] = useState(null);
  const [freshKey, setFreshKey] = useState(null);
  const draftRef = useRef(null);

  const refresh = async () => {
    if (!userEmail) return;
    setLoading(true); setError("");
    try {
      const params = { user_email: userEmail };
      if (filter !== "all") params.status = filter;
      const resp = await axios.get(`${API}/caos/captures`, { params, withCredentials: true });
      setCaptures(resp.data?.captures || []);
      setCounts(resp.data?.counts || { new: 0, promoted: 0, dismissed: 0 });
    } catch (issue) {
      setError(issue?.response?.data?.detail || issue?.message || "Failed to load captures");
    } finally {
      setLoading(false);
    }
  };

  const refreshKeyMeta = async () => {
    if (!userEmail) return;
    try {
      const resp = await axios.get(`${API}/caos/api-key`, {
        params: { user_email: userEmail },
        withCredentials: true,
      });
      setKeyMeta(resp.data);
    } catch { /* non-fatal */ }
  };

  useEffect(() => {
    if (isOpen) { refresh(); refreshKeyMeta(); }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, userEmail, filter]);

  const submitDraft = async () => {
    const text = draft.trim();
    if (!text) return;
    try {
      await axios.post(`${API}/caos/captures`,
        { text, source: "manual" },
        { withCredentials: true }
      );
      setDraft("");
      toast.success("Captured.");
      refresh();
      requestAnimationFrame(() => { draftRef.current?.focus(); });
    } catch (issue) {
      toast.error(issue?.response?.data?.detail || "Capture failed");
    }
  };

  const onDraftKey = (event) => {
    // Cmd/Ctrl + Enter to submit (like a chat composer).
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      submitDraft();
    }
  };

  const promote = async (cap) => {
    try {
      const resp = await axios.post(`${API}/caos/captures/${cap.id}/promote`,
        null, { params: { user_email: userEmail }, withCredentials: true });
      toast.success("Promoted to a new chat thread.");
      refresh();
      if (typeof onPromoted === "function") {
        onPromoted(resp.data?.session_id);
      }
    } catch (issue) {
      toast.error(issue?.response?.data?.detail || "Promote failed");
    }
  };

  const dismiss = async (cap) => {
    try {
      await axios.post(`${API}/caos/captures/${cap.id}/dismiss`,
        null, { params: { user_email: userEmail }, withCredentials: true });
      refresh();
    } catch (issue) {
      toast.error(issue?.response?.data?.detail || "Dismiss failed");
    }
  };

  const remove = async (cap) => {
    if (!window.confirm("Permanently delete this capture?")) return;
    try {
      await axios.delete(`${API}/caos/captures/${cap.id}`,
        { params: { user_email: userEmail }, withCredentials: true });
      toast.success("Deleted.");
      refresh();
    } catch (issue) {
      toast.error(issue?.response?.data?.detail || "Delete failed");
    }
  };

  const rotateKey = async () => {
    if (keyMeta?.has_key && !window.confirm(
      "Rotating will invalidate your current API key. Apple Shortcuts and any other ingest sources using the old key will stop working until you update them. Continue?"
    )) return;
    try {
      const resp = await axios.post(`${API}/caos/api-key/rotate`,
        null, { params: { user_email: userEmail }, withCredentials: true });
      setFreshKey(resp.data?.api_key);
      refreshKeyMeta();
      toast.success("New API key generated. Copy it now — you won't see it again.");
    } catch (issue) {
      toast.error(issue?.response?.data?.detail || "Rotate failed");
    }
  };

  const copyFreshKey = async () => {
    if (!freshKey) return;
    try {
      await navigator.clipboard.writeText(freshKey);
      toast.success("API key copied to clipboard.");
    } catch {
      toast.error("Clipboard write blocked. Select and copy manually.");
    }
  };

  const filteredCaptures = useMemo(() => captures, [captures]);

  if (!isOpen) return null;

  return (
    <div className="quick-capture-backdrop" data-testid="caos-capture-backdrop" onClick={onClose}>
      <div
        className="quick-capture-drawer"
        data-testid="caos-capture-drawer"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
      >
        <header className="quick-capture-header" data-testid="caos-capture-header">
          <div className="quick-capture-title">
            <Inbox size={16} />
            <h2 data-testid="caos-capture-title">Quick Capture</h2>
            <span className="quick-capture-count" data-testid="caos-capture-count">
              {counts.new} new · {counts.promoted} promoted
            </span>
          </div>
          <div className="quick-capture-header-actions">
            <button
              className="quick-capture-key-btn"
              data-testid="caos-capture-key-toggle"
              onClick={() => setShowKeyPanel((v) => !v)}
              type="button"
              title="API key for Apple Shortcut, pendants, and external scripts"
            >
              <Key size={12} />
              {keyMeta?.has_key ? "API key" : "Set up API"}
            </button>
            <button
              aria-label="Close Quick Capture"
              className="drawer-close-button"
              data-testid="caos-capture-close"
              onClick={onClose}
              type="button"
            >
              <X size={14} />
            </button>
          </div>
        </header>

        {showKeyPanel ? (
          <ApiKeyPanel
            freshKey={freshKey}
            keyMeta={keyMeta}
            onCopy={copyFreshKey}
            onDismiss={() => { setShowKeyPanel(false); setFreshKey(null); }}
            onRotate={rotateKey}
          />
        ) : null}

        <section className="quick-capture-composer" data-testid="caos-capture-composer">
          <textarea
            data-testid="caos-capture-draft"
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={onDraftKey}
            placeholder="Dump a thought… (Ctrl/Cmd+Enter to capture)"
            ref={draftRef}
            rows={2}
            value={draft}
          />
          <button
            className="quick-capture-submit"
            data-testid="caos-capture-submit"
            disabled={!draft.trim()}
            onClick={submitDraft}
            type="button"
          >
            <Send size={12} /> Capture
          </button>
        </section>

        <nav className="quick-capture-filters" data-testid="caos-capture-filters">
          {[
            { id: "new", label: "New", count: counts.new },
            { id: "promoted", label: "Promoted", count: counts.promoted },
            { id: "dismissed", label: "Dismissed", count: counts.dismissed },
            { id: "all", label: "All", count: counts.new + counts.promoted + counts.dismissed },
          ].map((f) => (
            <button
              className={`quick-capture-filter-tab ${filter === f.id ? "quick-capture-filter-tab-active" : ""}`}
              data-testid={`caos-capture-filter-${f.id}`}
              key={f.id}
              onClick={() => setFilter(f.id)}
              type="button"
            >
              {f.label}
              <span className="quick-capture-filter-count">{f.count}</span>
            </button>
          ))}
        </nav>

        <section className="quick-capture-list" data-testid="caos-capture-list">
          {error ? <div className="quick-capture-error" data-testid="caos-capture-error">{error}</div> : null}
          {loading ? <div className="quick-capture-loading">Loading…</div> : null}
          {!loading && !error && filteredCaptures.length === 0 ? (
            <div className="quick-capture-empty" data-testid="caos-capture-empty">
              {filter === "new"
                ? "Nothing captured yet. Type above, or send to your API key from an Apple Shortcut / Bee pendant."
                : "No captures in this view."}
            </div>
          ) : null}
          {filteredCaptures.map((cap) => (
            <CaptureCard
              capture={cap}
              key={cap.id}
              onDelete={() => remove(cap)}
              onDismiss={() => dismiss(cap)}
              onPromote={() => promote(cap)}
            />
          ))}
        </section>
      </div>
    </div>
  );
};


const CaptureCard = ({ capture, onPromote, onDismiss, onDelete }) => {
  const tone = SOURCE_PILLS[capture.source] || SOURCE_PILLS.manual;
  return (
    <article className={`quick-capture-card quick-capture-card-${capture.status}`} data-testid={`caos-capture-card-${capture.id}`}>
      <div className="quick-capture-card-meta">
        <span className={`quick-capture-source-pill ${tone.className}`} data-testid={`caos-capture-card-source-${capture.id}`}>
          {tone.label}
        </span>
        {capture.location ? (
          <span className="quick-capture-loc-pill" title="Captured location">@ {capture.location}</span>
        ) : null}
        <span className="quick-capture-time" title={capture.captured_at}>{formatRelative(capture.captured_at)}</span>
        {capture.atoms_extracted > 0 ? (
          <span className="quick-capture-atoms-pill" title="Memory atoms filed from this capture">
            {capture.atoms_extracted} atom{capture.atoms_extracted === 1 ? "" : "s"}
          </span>
        ) : null}
      </div>
      <p className="quick-capture-card-text" data-testid={`caos-capture-card-text-${capture.id}`}>
        {capture.text}
      </p>
      <div className="quick-capture-card-actions" data-testid={`caos-capture-card-actions-${capture.id}`}>
        {capture.status === "new" ? (
          <>
            <button
              className="quick-capture-promote-btn"
              data-testid={`caos-capture-promote-${capture.id}`}
              onClick={onPromote}
              type="button"
              title="Spawn a new chat thread pre-loaded with this capture"
            >
              <ArrowUpRight size={11} /> Promote to chat
            </button>
            <button
              className="quick-capture-dismiss-btn"
              data-testid={`caos-capture-dismiss-${capture.id}`}
              onClick={onDismiss}
              type="button"
            >
              Dismiss
            </button>
          </>
        ) : (
          <span className="quick-capture-card-status" data-testid={`caos-capture-card-status-${capture.id}`}>
            {capture.status === "promoted" ? "Promoted to chat" : "Dismissed"}
          </span>
        )}
        <button
          className="quick-capture-delete-btn"
          data-testid={`caos-capture-delete-${capture.id}`}
          onClick={onDelete}
          type="button"
          title="Permanently delete"
        >
          <Trash2 size={11} />
        </button>
      </div>
    </article>
  );
};


const ApiKeyPanel = ({ freshKey, keyMeta, onCopy, onDismiss, onRotate }) => (
  <section className="quick-capture-key-panel" data-testid="caos-capture-key-panel">
    <header>
      <h3>API key — for Apple Shortcut, Bee pendant, scripts</h3>
      <button aria-label="Close key panel" className="quick-capture-key-close"
              data-testid="caos-capture-key-panel-close" onClick={onDismiss} type="button">
        <X size={12} />
      </button>
    </header>
    {freshKey ? (
      <div className="quick-capture-fresh-key" data-testid="caos-capture-fresh-key">
        <div className="quick-capture-fresh-key-warn"><strong>Copy this NOW.</strong> You won&apos;t see it again — only the prefix.</div>
        <div className="quick-capture-fresh-key-row">
          <code data-testid="caos-capture-fresh-key-value">{freshKey}</code>
          <button data-testid="caos-capture-fresh-key-copy" onClick={onCopy} type="button">
            <Copy size={11} /> Copy
          </button>
        </div>
      </div>
    ) : null}
    <div className="quick-capture-key-meta" data-testid="caos-capture-key-meta">
      {keyMeta?.has_key ? (
        <>
          <p>Active key: <code>{keyMeta.prefix}</code></p>
          <p>Issued: {formatRelative(keyMeta.issued_at)}</p>
          {keyMeta.last_used_at ? <p>Last used: {formatRelative(keyMeta.last_used_at)}</p> : <p>Last used: never</p>}
        </>
      ) : (
        <p>No key yet. Generate one to enable external ingest (Apple Shortcut, Bee pendant, custom scripts).</p>
      )}
    </div>
    <button className="quick-capture-rotate-btn" data-testid="caos-capture-rotate-btn"
            onClick={onRotate} type="button">
      <RefreshCw size={11} />
      {keyMeta?.has_key ? "Rotate key" : "Generate API key"}
    </button>
    <details className="quick-capture-shortcut-tip">
      <summary><StickyNote size={11} /> Apple Shortcut snippet</summary>
      <pre>{`POST https://caosos.com/api/caos/captures
Headers:  Authorization: Bearer caos_…your_key…
          Content-Type: application/json
Body:     { "text": "<dictation>", "source": "shortcut" }`}</pre>
    </details>
  </section>
);

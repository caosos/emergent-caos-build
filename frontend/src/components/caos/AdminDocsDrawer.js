import axios from "axios";
import { BookOpen, FileText, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Ultra-lightweight markdown renderer. Safe because content comes from
// admin-gated server endpoints reading the repo's /app/memory/*.md files.
const renderMarkdown = (md) => {
  if (!md) return "";
  const escape = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const lines = md.split(/\r?\n/);
  const out = [];
  let inCode = false;
  let inList = false;
  const flushList = () => { if (inList) { out.push("</ul>"); inList = false; } };
  lines.forEach((raw) => {
    const line = raw;
    if (line.trim().startsWith("```")) {
      flushList();
      out.push(inCode ? "</code></pre>" : "<pre class=\"admin-docs-code\"><code>");
      inCode = !inCode;
      return;
    }
    if (inCode) { out.push(`${escape(line)}\n`); return; }
    if (/^#\s+/.test(line)) { flushList(); out.push(`<h1>${escape(line.replace(/^#\s+/, ""))}</h1>`); return; }
    if (/^##\s+/.test(line)) { flushList(); out.push(`<h2>${escape(line.replace(/^##\s+/, ""))}</h2>`); return; }
    if (/^###\s+/.test(line)) { flushList(); out.push(`<h3>${escape(line.replace(/^###\s+/, ""))}</h3>`); return; }
    if (/^####\s+/.test(line)) { flushList(); out.push(`<h4>${escape(line.replace(/^####\s+/, ""))}</h4>`); return; }
    if (/^[-*]\s+/.test(line)) {
      if (!inList) { out.push("<ul>"); inList = true; }
      let item = escape(line.replace(/^[-*]\s+/, ""));
      item = item.replace(/`([^`]+)`/g, "<code>$1</code>").replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
      out.push(`<li>${item}</li>`);
      return;
    }
    flushList();
    if (!line.trim()) { out.push("<br/>"); return; }
    let para = escape(line)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    out.push(`<p>${para}</p>`);
  });
  flushList();
  if (inCode) out.push("</code></pre>");
  return out.join("\n");
};

export const AdminDocsDrawer = ({ isOpen, onClose }) => {
  const [docs, setDocs] = useState([]);
  const [activeFilename, setActiveFilename] = useState(null);
  const [content, setContent] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;
    setError("");
    (async () => {
      try {
        const response = await axios.get(`${API}/admin/docs`, { withCredentials: true });
        if (cancelled) return;
        const list = response.data?.documents || [];
        setDocs(list);
        if (list.length && !activeFilename) setActiveFilename(list[0].filename);
      } catch (issue) {
        if (cancelled) return;
        setError(issue?.response?.data?.detail || issue?.message || "Failed to load docs");
      }
    })();
    return () => { cancelled = true; };
  }, [isOpen, activeFilename]);

  useEffect(() => {
    if (!isOpen || !activeFilename) return;
    let cancelled = false;
    setLoading(true);
    setError("");
    (async () => {
      try {
        const response = await axios.get(`${API}/admin/docs/${activeFilename}`, { withCredentials: true });
        if (!cancelled) setContent(response.data?.content || "");
      } catch (issue) {
        if (!cancelled) setError(issue?.response?.data?.detail || issue?.message || "Failed to load doc");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => { cancelled = true; };
  }, [activeFilename, isOpen]);

  const rendered = useMemo(() => renderMarkdown(content), [content]);

  if (!isOpen) return null;

  return (
    <div className="admin-docs-backdrop" data-testid="caos-admin-docs-backdrop" onClick={onClose}>
      <div
        className="admin-docs-drawer"
        data-testid="caos-admin-docs-drawer"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <div className="admin-docs-header" data-testid="caos-admin-docs-header">
          <div className="admin-docs-header-title">
            <BookOpen size={16} />
            <h2 data-testid="caos-admin-docs-title">Admin Docs · Project Blueprints</h2>
          </div>
          <button
            aria-label="Close admin docs"
            className="drawer-close-button"
            data-testid="caos-admin-docs-close-button"
            onClick={onClose}
            type="button"
          >
            <X size={14} />
          </button>
        </div>
        <div className="admin-docs-body" data-testid="caos-admin-docs-body">
          <nav className="admin-docs-nav" data-testid="caos-admin-docs-nav">
            {docs.length === 0 && !error ? (
              <div className="admin-docs-empty" data-testid="caos-admin-docs-empty">Loading…</div>
            ) : null}
            {docs.map((doc) => (
              <button
                className={`admin-docs-nav-item ${activeFilename === doc.filename ? "admin-docs-nav-item-active" : ""}`}
                data-testid={`caos-admin-docs-nav-${doc.filename}`}
                key={doc.filename}
                onClick={() => setActiveFilename(doc.filename)}
                type="button"
              >
                <FileText size={12} />
                <span>{doc.filename}</span>
              </button>
            ))}
          </nav>
          <article className="admin-docs-content" data-testid="caos-admin-docs-content">
            {error ? <div className="admin-docs-error" data-testid="caos-admin-docs-error">{error}</div> : null}
            {loading ? <div className="admin-docs-loading" data-testid="caos-admin-docs-loading">Loading document…</div> : null}
            {!loading && !error ? (
              <div
                className="admin-docs-markdown"
                data-testid="caos-admin-docs-markdown"
                dangerouslySetInnerHTML={{ __html: rendered }}
              />
            ) : null}
          </article>
        </div>
      </div>
    </div>
  );
};

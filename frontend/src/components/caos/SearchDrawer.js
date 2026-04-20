import { Search, X } from "lucide-react";
import { useMemo } from "react";


const roleLabel = (role) => role === "assistant" ? "CAOS" : role === "user" ? "You" : "System";


const highlightText = (text, needle) => {
  if (!needle || !text) return text;
  const safe = needle.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const parts = String(text).split(new RegExp(`(${safe})`, "gi"));
  return parts.map((part, index) =>
    part.toLowerCase() === needle.toLowerCase()
      ? <mark className="search-highlight" data-testid={`caos-search-hit-highlight-${index}`} key={index}>{part}</mark>
      : <span key={index}>{part}</span>
  );
};


const buildSnippet = (text, needle) => {
  if (!needle) return text?.slice(0, 220) || "";
  const source = String(text || "");
  const index = source.toLowerCase().indexOf(needle.toLowerCase());
  if (index < 0) return source.slice(0, 220);
  const start = Math.max(0, index - 80);
  const end = Math.min(source.length, index + needle.length + 120);
  const prefix = start > 0 ? "…" : "";
  const suffix = end < source.length ? "…" : "";
  return `${prefix}${source.slice(start, end)}${suffix}`;
};


export const SearchDrawer = ({ currentSession, isOpen, onClose, results, searchQuery, setSearchQuery }) => {
  const matchCount = useMemo(() => {
    if (!searchQuery.trim()) return 0;
    const needle = searchQuery.toLowerCase();
    return results.reduce((count, message) => {
      const occurrences = String(message.content || "").toLowerCase().split(needle).length - 1;
      return count + occurrences;
    }, 0);
  }, [results, searchQuery]);

  if (!isOpen) return null;

  return (
    <aside className="search-drawer" data-testid="caos-search-drawer">
      <div className="search-drawer-header" data-testid="caos-search-drawer-header">
        <strong data-testid="caos-search-drawer-title">Search Thread</strong>
        <button className="drawer-close-button" data-testid="caos-search-drawer-close-button" onClick={onClose}>
          <X size={14} />
        </button>
      </div>
      <div className="side-panel-meta" data-testid="caos-search-drawer-meta">
        <span data-testid="caos-search-drawer-thread-title">{currentSession?.title || "No active thread"}</span>
        <strong data-testid="caos-search-drawer-result-count">
          {searchQuery.trim() ? `${matchCount} match${matchCount === 1 ? "" : "es"} in ${results.length} message${results.length === 1 ? "" : "s"}` : "Type to search"}
        </strong>
      </div>
      <label className="search-drawer-input-row" data-testid="caos-search-drawer-input-row">
        <Search size={14} />
        <input
          autoFocus
          data-testid="caos-thread-search-input"
          placeholder="Search this thread"
          value={searchQuery}
          onChange={(event) => setSearchQuery(event.target.value)}
        />
      </label>
      <div className="search-drawer-results" data-testid="caos-search-drawer-results">
        {!searchQuery.trim() ? (
          <article className="search-hit" data-testid="caos-search-hit-empty">
            <p>Type to search the active thread.</p>
          </article>
        ) : results.length === 0 ? (
          <article className="search-hit" data-testid="caos-search-hit-none">
            <p>No matches found.</p>
          </article>
        ) : null}
        {results.map((message, index) => (
          <article className="search-hit" data-testid={`caos-search-hit-${message.id}`} key={message.id}>
            <div className="search-hit-meta" data-testid={`caos-search-hit-meta-${message.id}`}>
              <span data-testid={`caos-search-hit-index-${message.id}`}>#{index + 1} {roleLabel(message.role)}</span>
              <strong data-testid={`caos-search-hit-time-${message.id}`}>{new Date(message.timestamp).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</strong>
            </div>
            <p data-testid={`caos-search-hit-content-${message.id}`}>
              {highlightText(buildSnippet(message.content, searchQuery), searchQuery)}
            </p>
          </article>
        ))}
      </div>
    </aside>
  );
};

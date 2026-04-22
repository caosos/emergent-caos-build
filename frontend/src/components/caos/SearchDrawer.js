import { useMemo } from "react";

const roleLabel = (role) => (role === "assistant" ? "CAOS" : role === "user" ? "You" : "System");

const escapeRe = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

const highlightText = (text, needle) => {
  if (!needle || !text) return text;
  const parts = String(text).split(new RegExp(`(${escapeRe(needle)})`, "gi"));
  return parts.map((part, index) =>
    part.toLowerCase() === needle.toLowerCase()
      ? <mark className="search-highlight" key={index}>{part}</mark>
      : <span key={index}>{part}</span>
  );
};

const buildSnippet = (text, needle) => {
  if (!needle) return text?.slice(0, 180) || "";
  const source = String(text || "");
  const index = source.toLowerCase().indexOf(needle.toLowerCase());
  if (index < 0) return source.slice(0, 180);
  const start = Math.max(0, index - 60);
  const end = Math.min(source.length, index + needle.length + 100);
  const prefix = start > 0 ? "…" : "";
  const suffix = end < source.length ? "…" : "";
  return `${prefix}${source.slice(start, end)}${suffix}`;
};

/**
 * Base44-parity right-side search panel. Header owns the query input; this
 * panel just renders the numbered match cards (#1 CAOS / #2 You) with yellow
 * <mark> highlights on the matched term.
 */
export const SearchDrawer = ({ isOpen, onJumpTo, results, searchQuery }) => {
  const hasQuery = searchQuery.trim().length > 0;
  const matchCount = useMemo(() => {
    if (!hasQuery) return 0;
    const needle = searchQuery.toLowerCase();
    return results.reduce((count, message) => {
      const occurrences = String(message.content || "").toLowerCase().split(needle).length - 1;
      return count + occurrences;
    }, 0);
  }, [results, searchQuery, hasQuery]);

  if (!isOpen || !hasQuery) return null;

  return (
    <aside className="thread-search-panel" data-testid="caos-search-drawer">
      <div className="thread-search-panel-header" data-testid="caos-search-drawer-header">
        <span className="thread-search-panel-query" data-testid="caos-search-drawer-query">Searching “{searchQuery}”</span>
        <span className="thread-search-panel-count" data-testid="caos-search-drawer-result-count">
          {matchCount} {matchCount === 1 ? "match" : "matches"}
        </span>
      </div>
      <div className="thread-search-panel-list" data-testid="caos-search-drawer-results">
        {results.length === 0 ? (
          <div className="thread-search-empty" data-testid="caos-search-hit-none">No matches in this thread.</div>
        ) : null}
        {results.map((message, index) => (
          <button
            className="thread-search-hit"
            data-testid={`caos-search-hit-${message.id}`}
            key={message.id}
            onClick={() => onJumpTo?.(message.id)}
            type="button"
          >
            <div className="thread-search-hit-meta">
              <span className="thread-search-hit-index" data-testid={`caos-search-hit-index-${message.id}`}>
                #{index + 1}
              </span>
              <span className={`thread-search-hit-role thread-search-hit-role-${message.role}`} data-testid={`caos-search-hit-role-${message.id}`}>
                {roleLabel(message.role)}
              </span>
            </div>
            <p data-testid={`caos-search-hit-content-${message.id}`}>
              {highlightText(buildSnippet(message.content, searchQuery), searchQuery)}
            </p>
          </button>
        ))}
      </div>
    </aside>
  );
};

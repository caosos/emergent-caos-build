import { Search, X } from "lucide-react";


export const SearchDrawer = ({ isOpen, onClose, results, searchQuery, setSearchQuery }) => {
  if (!isOpen) return null;

  return (
    <aside className="search-drawer" data-testid="caos-search-drawer">
      <div className="search-drawer-header" data-testid="caos-search-drawer-header">
        <strong data-testid="caos-search-drawer-title">Search Thread</strong>
        <button className="drawer-close-button" data-testid="caos-search-drawer-close-button" onClick={onClose}>
          <X size={14} />
        </button>
      </div>
      <label className="search-drawer-input-row" data-testid="caos-search-drawer-input-row">
        <Search size={14} />
        <input
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
        ) : null}
        {results.map((message, index) => (
          <article className="search-hit" data-testid={`caos-search-hit-${message.id}`} key={message.id}>
            <span data-testid={`caos-search-hit-index-${message.id}`}>#{index + 1} {message.role === 'assistant' ? 'CAOS' : 'You'}</span>
            <p data-testid={`caos-search-hit-content-${message.id}`}>{message.content}</p>
          </article>
        ))}
      </div>
    </aside>
  );
};
export const SearchDrawer = ({ results, searchQuery }) => {
  if (!searchQuery.trim()) return null;

  return (
    <aside className="search-drawer" data-testid="caos-search-drawer">
      <div className="search-drawer-header" data-testid="caos-search-drawer-header">
        <strong data-testid="caos-search-drawer-title">Search Results</strong>
        <span data-testid="caos-search-drawer-query">{searchQuery}</span>
      </div>
      <div className="search-drawer-results" data-testid="caos-search-drawer-results">
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
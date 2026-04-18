import { AlertTriangle, Brain, FileText, Search } from "lucide-react";

import { Composer } from "@/components/caos/Composer";
import { MessagePane } from "@/components/caos/MessagePane";
import { ShellHeader } from "@/components/caos/ShellHeader";
import { ThreadRail } from "@/components/caos/ThreadRail";
import { useCaosShell } from "@/components/caos/useCaosShell";


export const CaosShell = () => {
  const {
    busy,
    createSession,
    currentSession,
    error,
    filteredMessages,
    lastTurn,
    searchQuery,
    selectSession,
    sendMessage,
    sessions,
    setSearchQuery,
    setUserEmail,
    status,
    userEmail,
  } = useCaosShell();

  return (
    <main className="caos-shell-root" data-testid="caos-shell-root">
      <ShellHeader
        onNewSession={() => createSession()}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        setUserEmail={setUserEmail}
        userEmail={userEmail}
        wcwBudget={lastTurn?.wcw_budget || 200000}
        wcwUsed={lastTurn?.wcw_used_estimate || 0}
      />

      <div className="caos-shell-grid" data-testid="caos-shell-grid">
        <ThreadRail
          currentSessionId={currentSession?.session_id}
          onSelectSession={selectSession}
          sessions={sessions}
        />

        <section className="caos-main-column" data-testid="caos-main-column">
          {error ? (
            <div className="shell-error-banner" data-testid="caos-error-banner">
              <AlertTriangle size={16} />
              <span data-testid="caos-error-text">{error}</span>
            </div>
          ) : null}

          <MessagePane busy={busy} currentSession={currentSession} messages={filteredMessages} />
          <Composer busy={busy} onSend={sendMessage} status={status} />
        </section>

        <aside className="context-column" data-testid="caos-context-column">
          <section className="context-card" data-testid="caos-receipt-card">
            <div className="context-card-heading">
              <Brain size={16} />
              <h2 data-testid="caos-receipt-heading">Turn Receipt</h2>
            </div>
            <div className="context-metric" data-testid="caos-receipt-reduction">
              <span>Reduction ratio</span>
              <strong>{Math.round((lastTurn?.receipt?.reduction_ratio || 0) * 100)}%</strong>
            </div>
            <div className="context-metric" data-testid="caos-receipt-retrieval-terms">
              <span>Retrieval terms</span>
              <strong>{lastTurn?.receipt?.retrieval_terms?.join(", ") || "No turn yet"}</strong>
            </div>
            <div className="context-metric" data-testid="caos-receipt-memory-count">
              <span>Injected memories</span>
              <strong>{lastTurn?.receipt?.injected_memory_count || 0}</strong>
            </div>
          </section>

          <section className="context-card" data-testid="caos-memory-card">
            <div className="context-card-heading">
              <FileText size={16} />
              <h2 data-testid="caos-memory-heading">Injected Memory</h2>
            </div>
            <div className="context-list" data-testid="caos-memory-list">
              {(lastTurn?.injected_memories || []).map((memory) => (
                <div className="context-list-item" data-testid={`caos-memory-item-${memory.id}`} key={memory.id}>
                  {memory.content}
                </div>
              ))}
              {!lastTurn?.injected_memories?.length ? (
                <div className="context-list-item context-list-placeholder" data-testid="caos-memory-empty-state">
                  No memory injected yet.
                </div>
              ) : null}
            </div>
          </section>

          <section className="context-card" data-testid="caos-search-summary-card">
            <div className="context-card-heading">
              <Search size={16} />
              <h2 data-testid="caos-search-summary-heading">Thread Search</h2>
            </div>
            <p data-testid="caos-search-summary-text">
              {searchQuery ? `Showing messages matching “${searchQuery}”.` : "Use the header search to filter the active session instantly."}
            </p>
          </section>
        </aside>
      </div>
    </main>
  );
};
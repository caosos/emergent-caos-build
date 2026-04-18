import { useState } from "react";
import { AlertTriangle, Brain, FileText, Search } from "lucide-react";

import { ArtifactsDrawer } from "@/components/caos/ArtifactsDrawer";
import { Composer } from "@/components/caos/Composer";
import { MessagePane } from "@/components/caos/MessagePane";
import { ProfileDrawer } from "@/components/caos/ProfileDrawer";
import { ShellHeader } from "@/components/caos/ShellHeader";
import { ThreadRail } from "@/components/caos/ThreadRail";
import { useCaosShell } from "@/components/caos/useCaosShell";


export const CaosShell = () => {
  const [showArtifacts, setShowArtifacts] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const {
    artifacts,
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
    profile,
  } = useCaosShell();
  const latestReceipt = lastTurn?.receipt || (artifacts.receipts[0]
    ? {
        retrieval_terms: artifacts.receipts[0].retrieval_terms,
        reduction_ratio: artifacts.receipts[0].reduction_ratio,
        injected_memory_count: artifacts.receipts[0].selected_memory_ids?.length || 0,
      }
    : null);
  const memorySurface = lastTurn?.injected_memories || [];

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
          <div className="surface-button-row" data-testid="caos-surface-button-row">
            <button className="surface-button" data-testid="caos-open-profile-button" onClick={() => setShowProfile(true)}>Profile</button>
            <button className="surface-button" data-testid="caos-open-artifacts-button" onClick={() => setShowArtifacts(true)}>Files & Artifacts</button>
          </div>

          <section className="context-card" data-testid="caos-receipt-card">
            <div className="context-card-heading">
              <Brain size={16} />
              <h2 data-testid="caos-receipt-heading">Turn Receipt</h2>
            </div>
            <div className="context-metric" data-testid="caos-receipt-reduction">
              <span>Reduction ratio</span>
              <strong>{Math.round((latestReceipt?.reduction_ratio || 0) * 100)}%</strong>
            </div>
            <div className="context-metric" data-testid="caos-receipt-retrieval-terms">
              <span>Retrieval terms</span>
              <strong>{latestReceipt?.retrieval_terms?.join(", ") || "No turn yet"}</strong>
            </div>
            <div className="context-metric" data-testid="caos-receipt-memory-count">
              <span>Injected memories</span>
              <strong>{latestReceipt?.injected_memory_count || 0}</strong>
            </div>
          </section>

          <section className="context-card" data-testid="caos-memory-card">
            <div className="context-card-heading">
              <FileText size={16} />
              <h2 data-testid="caos-memory-heading">Injected Memory</h2>
            </div>
            <div className="context-list" data-testid="caos-memory-list">
              {memorySurface.map((memory) => (
                <div className="context-list-item" data-testid={`caos-memory-item-${memory.id}`} key={memory.id}>
                  {memory.content}
                </div>
              ))}
              {!memorySurface.length ? (
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

      <ProfileDrawer
        isOpen={showProfile}
        memoryCount={profile?.structured_memory?.length || 0}
        onClose={() => setShowProfile(false)}
        profile={profile}
        sessionsCount={sessions.length}
        userEmail={userEmail}
      />
      <ArtifactsDrawer artifacts={artifacts} isOpen={showArtifacts} onClose={() => setShowArtifacts(false)} />
    </main>
  );
};
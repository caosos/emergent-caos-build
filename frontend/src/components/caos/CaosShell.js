import { useState } from "react";
import { AlertTriangle, Brain, FileText, Search } from "lucide-react";

import { ArtifactsDrawer } from "@/components/caos/ArtifactsDrawer";
import { Composer } from "@/components/caos/Composer";
import { MessagePane } from "@/components/caos/MessagePane";
import { ProfileDrawer } from "@/components/caos/ProfileDrawer";
import { SearchDrawer } from "@/components/caos/SearchDrawer";
import { ShellHeader } from "@/components/caos/ShellHeader";
import { ThreadRail } from "@/components/caos/ThreadRail";
import { useCaosShell } from "@/components/caos/useCaosShell";


export const CaosShell = () => {
  const [showArtifacts, setShowArtifacts] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const {
    artifacts,
    busy,
    commitUserEmail,
    continuity,
    createSession,
    currentSession,
    error,
    filteredMessages,
    files,
    lastTurn,
    searchQuery,
    saveLink,
    selectSession,
    sendMessage,
    sessions,
    setSearchQuery,
    speakText,
    status,
    transcribeAudio,
    uploadFile,
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
        currentSession={currentSession}
        onToggleSearch={() => setShowSearch((value) => !value)}
        wcwBudget={lastTurn?.wcw_budget || 200000}
        wcwUsed={lastTurn?.wcw_used_estimate || 0}
      />

      <div className="caos-shell-grid caos-shell-grid-layout" data-testid="caos-shell-grid">
        <ThreadRail
          currentSessionId={currentSession?.session_id}
          onNewSession={() => createSession()}
          onOpenArtifacts={() => setShowArtifacts(true)}
          onOpenProfile={() => setShowProfile(true)}
          onSelectSession={selectSession}
          sessions={sessions}
          userEmail={userEmail}
        />

        <section className="caos-main-column" data-testid="caos-main-column">
          {error ? (
            <div className="shell-error-banner" data-testid="caos-error-banner">
              <AlertTriangle size={16} />
              <span data-testid="caos-error-text">{error}</span>
            </div>
          ) : null}

          <MessagePane busy={busy} currentSession={currentSession} messages={filteredMessages} onSpeak={speakText} receipts={artifacts.receipts} />
          <Composer busy={busy} onSend={sendMessage} onTranscribe={transcribeAudio} onUploadFile={uploadFile} status={status} />
        </section>

        {!showSearch ? (
          <aside className="context-column" data-testid="caos-context-column">
            <section className="context-card" data-testid="caos-receipt-card">
              <div className="context-card-heading">
                <Brain size={16} />
                <h2 data-testid="caos-receipt-heading">Why this reply fits</h2>
              </div>
              <div className="context-metric" data-testid="caos-receipt-reduction">
                <span>Context trimmed</span>
                <strong>{Math.round((latestReceipt?.reduction_ratio || 0) * 100)}%</strong>
              </div>
              <div className="context-metric" data-testid="caos-receipt-retrieval-terms">
                <span>Used for recall</span>
                <strong>{latestReceipt?.retrieval_terms?.join(", ") || "No turn yet"}</strong>
              </div>
              <div className="context-metric" data-testid="caos-receipt-memory-count">
                <span>Memories carried</span>
                <strong>{latestReceipt?.injected_memory_count || 0}</strong>
              </div>
            </section>

            <section className="context-card" data-testid="caos-continuity-card">
              <div className="context-card-heading">
                <Brain size={16} />
                <h2 data-testid="caos-continuity-heading">Carried forward</h2>
              </div>
              <div className="context-metric" data-testid="caos-continuity-depth">
                <span>Thread depth</span>
                <strong>{continuity?.lineage_depth || 0}</strong>
              </div>
              <div className="context-list-item" data-testid="caos-continuity-summary">
                {continuity?.latest_summary?.summary || "No continuity summary yet."}
              </div>
            </section>

            {memorySurface.length ? (
              <section className="context-card" data-testid="caos-memory-card">
                <div className="context-card-heading">
                  <FileText size={16} />
                  <h2 data-testid="caos-memory-heading">Memory in play</h2>
                </div>
                <div className="context-list" data-testid="caos-memory-list">
                  {memorySurface.map((memory) => (
                    <div className="context-list-item" data-testid={`caos-memory-item-${memory.id}`} key={memory.id}>
                      {memory.content}
                    </div>
                  ))}
                </div>
              </section>
            ) : null}
          </aside>
        ) : null}
      </div>

      <SearchDrawer
        isOpen={showSearch}
        onClose={() => setShowSearch(false)}
        results={filteredMessages.slice(0, 8)}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
      />

      <ProfileDrawer
        isOpen={showProfile}
        memoryCount={profile?.structured_memory?.length || 0}
        onClose={() => setShowProfile(false)}
        profile={profile}
        sessionsCount={sessions.length}
        userEmail={userEmail}
      />
      <ArtifactsDrawer
        artifacts={artifacts}
        files={files}
        isOpen={showArtifacts}
        onClose={() => setShowArtifacts(false)}
        onSaveLink={saveLink}
        onUploadFile={uploadFile}
      />
    </main>
  );
};
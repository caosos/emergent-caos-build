import { useState } from "react";
import { AlertTriangle } from "lucide-react";

import { ArtifactsDrawer } from "@/components/caos/ArtifactsDrawer";
import { Composer } from "@/components/caos/Composer";
import { InspectorPanel } from "@/components/caos/InspectorPanel";
import { MessagePane } from "@/components/caos/MessagePane";
import { ModelBar } from "@/components/caos/ModelBar";
import { ProfileDrawer } from "@/components/caos/ProfileDrawer";
import { QuickActionsStrip } from "@/components/caos/QuickActionsStrip";
import { SearchDrawer } from "@/components/caos/SearchDrawer";
import { ShellHeader } from "@/components/caos/ShellHeader";
import { ThreadRail } from "@/components/caos/ThreadRail";
import { useCaosShell } from "@/components/caos/useCaosShell";


export const CaosShell = () => {
  const [isRailOpen, setIsRailOpen] = useState(true);
  const [showArtifacts, setShowArtifacts] = useState(false);
  const [showInspector, setShowInspector] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const {
    artifacts,
    busy,
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
    runtimeSettings,
    updateRuntimeSelection,
  } = useCaosShell();
  const latestReceipt = lastTurn?.receipt || (artifacts.receipts[0]
    ? {
        retrieval_terms: artifacts.receipts[0].retrieval_terms,
        reduction_ratio: artifacts.receipts[0].reduction_ratio,
        injected_memory_count: artifacts.receipts[0].selected_memory_ids?.length || 0,
      }
    : null);
  const memorySurface = lastTurn?.injected_memories || [];
  const lastAssistantMessage = [...filteredMessages].reverse().find((message) => message.role === "assistant") || null;

  return (
    <main className={`caos-shell-root ${isRailOpen ? "caos-shell-rail-open" : "caos-shell-rail-closed"}`} data-testid="caos-shell-root">
      <ShellHeader
        activeModel={runtimeSettings.default_model}
        activeProvider={runtimeSettings.default_provider}
        currentSession={currentSession}
        isRailOpen={isRailOpen}
        keySource={runtimeSettings.key_source}
        onToggleRail={() => setIsRailOpen((value) => !value)}
        onToggleSearch={() => setShowSearch((value) => !value)}
        wcwBudget={lastTurn?.wcw_budget || 200000}
        wcwUsed={lastTurn?.wcw_used_estimate || 0}
      />

      <div className="caos-shell-grid caos-shell-grid-layout" data-testid="caos-shell-grid">
        <ThreadRail
          currentSessionId={currentSession?.session_id}
          isCollapsed={!isRailOpen}
          onNewSession={() => createSession()}
          onOpenArtifacts={() => setShowArtifacts(true)}
          onOpenProfile={() => setShowProfile(true)}
          onSelectSession={selectSession}
          onToggleRail={() => setIsRailOpen((value) => !value)}
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
        </section>
      </div>

      <div className="command-footer" data-testid="caos-command-footer">
        <QuickActionsStrip onContinueThread={() => createSession("Continued Thread")} onOpenArtifacts={() => setShowArtifacts(true)} />
        <ModelBar
          activeModel={runtimeSettings.default_model}
          activeProvider={runtimeSettings.default_provider}
          keySource={runtimeSettings.key_source}
          onSelect={updateRuntimeSelection}
          providerCatalog={runtimeSettings.provider_catalog}
        />
        <Composer
          busy={busy}
          lastAssistantMessage={lastAssistantMessage}
          onSend={sendMessage}
          onSpeak={speakText}
          onTranscribe={transcribeAudio}
          onUploadFile={uploadFile}
          status={status}
        />
      </div>

      {!showSearch ? (
        <button className="inspector-toggle-button" data-testid="caos-inspector-toggle-button" onClick={() => setShowInspector((value) => !value)}>
          Insights
        </button>
      ) : null}

      <InspectorPanel
        continuity={continuity}
        isOpen={showInspector && !showSearch}
        latestReceipt={latestReceipt}
        memorySurface={memorySurface}
        onClose={() => setShowInspector(false)}
      />

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
        runtimeSettings={runtimeSettings}
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
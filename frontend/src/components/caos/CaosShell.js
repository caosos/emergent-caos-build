import { useState } from "react";
import { AlertTriangle } from "lucide-react";

import { ArtifactsDrawer } from "@/components/caos/ArtifactsDrawer";
import { Composer } from "@/components/caos/Composer";
import { InspectorPanel } from "@/components/caos/InspectorPanel";
import { MessagePane } from "@/components/caos/MessagePane";
import { ModelBar } from "@/components/caos/ModelBar";
import { PreviousThreadsPanel } from "@/components/caos/PreviousThreadsPanel";
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
  const [showThreadExplorer, setShowThreadExplorer] = useState(false);
  const {
    artifacts,
    busy,
    continuity,
    createSession,
    currentSession,
    deleteMemory,
    error,
    filteredMessages,
    files,
    lastTurn,
    searchQuery,
    saveLink,
    saveMemory,
    selectSession,
    sendMessage,
    sessions,
    setSearchQuery,
    speakText,
    status,
    transcribeAudio,
    transcribeAudioChunk,
    uploadFile,
    userEmail,
    profile,
    runtimeSettings,
    updateRuntimeSelection,
    updateMemory,
    updateVoiceSettings,
    voiceSettings,
  } = useCaosShell();
  const latestReceipt = lastTurn?.receipt
    ? {
        ...(artifacts.receipts[0] || {}),
        ...lastTurn.receipt,
        provider: lastTurn.provider,
        model: lastTurn.model,
        lane: lastTurn.lane,
        subject_bins: lastTurn.subject_bins,
      }
    : (artifacts.receipts[0] || null);
  const memorySurface = lastTurn?.injected_memories || [];
  const lastAssistantMessage = [...filteredMessages].reverse().find((message) => message.role === "assistant") || null;
  const activeSurface = showSearch
    ? "search"
    : showThreadExplorer
      ? "threads"
      : showInspector
        ? "tools"
        : showProfile
          ? "models"
          : showArtifacts
            ? "projects"
            : "chat";
  const showCommandToolbar = activeSurface === "chat";

  const focusChat = () => {
    setShowArtifacts(false);
    setShowInspector(false);
    setShowProfile(false);
    setShowSearch(false);
    setShowThreadExplorer(false);
  };

  const openInspector = () => {
    setShowArtifacts(false);
    setShowProfile(false);
    setShowSearch(false);
    setShowThreadExplorer(false);
    setShowInspector(true);
  };

  const openArtifacts = () => {
    setShowInspector(false);
    setShowProfile(false);
    setShowSearch(false);
    setShowThreadExplorer(false);
    setShowArtifacts(true);
  };

  const openProfile = () => {
    setShowArtifacts(false);
    setShowInspector(false);
    setShowProfile(true);
    setShowSearch(false);
    setShowThreadExplorer(false);
  };

  const openSearch = () => {
    setShowArtifacts(false);
    setShowProfile(false);
    setShowSearch(true);
    setShowInspector(false);
    setShowThreadExplorer(false);
  };

  const toggleThreads = () => {
    setShowArtifacts(false);
    setShowProfile(false);
    setShowSearch(false);
    setShowInspector(false);
    setShowThreadExplorer((value) => !value);
  };

  return (
    <main className={`caos-shell-root ${isRailOpen ? "caos-shell-rail-open" : "caos-shell-rail-closed"}`} data-testid="caos-shell-root">
      <ShellHeader
        activeSurface={activeSurface}
        currentSession={currentSession}
        isRailOpen={isRailOpen}
        onOpenThreads={toggleThreads}
        onToggleRail={() => setIsRailOpen((value) => !value)}
        onToggleSearch={openSearch}
      />

      <div className="caos-shell-grid caos-shell-grid-layout" data-testid="caos-shell-grid">
        <ThreadRail
          activeSurface={activeSurface}
          currentSessionId={currentSession?.session_id}
          isCollapsed={!isRailOpen}
          onFocusChat={focusChat}
          onNewSession={() => createSession()}
          onOpenArtifacts={openArtifacts}
          onOpenInspector={openInspector}
          onOpenProfile={openProfile}
          onOpenSearch={openSearch}
          onOpenThreads={toggleThreads}
          onSelectSession={selectSession}
          onToggleRail={() => setIsRailOpen((value) => !value)}
          profile={profile}
          runtimeSettings={runtimeSettings}
          sessions={sessions}
          userEmail={userEmail}
          wcwBudget={latestReceipt?.wcw_budget || lastTurn?.wcw_budget || 200000}
          wcwUsed={latestReceipt?.active_context_tokens || lastTurn?.wcw_used_estimate || 0}
          wcwSent={latestReceipt?.prompt_tokens || 0}
          wcwReceived={latestReceipt?.completion_tokens || 0}
        />

        <section className="caos-main-column" data-testid="caos-main-column">
          {error ? (
            <div className="shell-error-banner" data-testid="caos-error-banner">
              <AlertTriangle size={16} />
              <span data-testid="caos-error-text">{error}</span>
            </div>
          ) : null}

          <MessagePane
            busy={busy}
            currentSession={currentSession}
            messages={filteredMessages}
            onSpeak={speakText}
            receipts={artifacts.receipts}
          />
        </section>
      </div>

      <PreviousThreadsPanel
        currentSessionId={currentSession?.session_id}
        isOpen={showThreadExplorer}
        onClose={() => setShowThreadExplorer(false)}
        onSelectSession={selectSession}
        sessions={sessions}
      />

      <div className="command-footer" data-testid="caos-command-footer">
        <div className="command-footer-inner" data-testid="caos-command-footer-inner">
          {showCommandToolbar ? (
            <div className="command-footer-toolbar" data-testid="caos-command-footer-toolbar">
              <QuickActionsStrip onContinueThread={() => createSession("Continued Thread")} onOpenArtifacts={openArtifacts} />
              <ModelBar
                activeModel={runtimeSettings.default_model}
                activeProvider={runtimeSettings.default_provider}
                keySource={runtimeSettings.key_source}
                onSelect={updateRuntimeSelection}
                providerCatalog={runtimeSettings.provider_catalog}
              />
            </div>
          ) : null}
          <Composer
            busy={busy}
            lastAssistantMessage={lastAssistantMessage}
            onSend={sendMessage}
            onSpeak={speakText}
            onTranscribe={transcribeAudio}
            onTranscribeChunk={transcribeAudioChunk}
            onUploadFile={uploadFile}
            status={status}
            voiceSettings={voiceSettings}
          />
        </div>
      </div>
      <InspectorPanel
        continuity={continuity}
        isOpen={showInspector && !showSearch}
        latestReceipt={latestReceipt}
        memorySurface={memorySurface}
        onClose={() => setShowInspector(false)}
      />

      <SearchDrawer
        currentSession={currentSession}
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
        deleteMemory={deleteMemory}
        profile={profile}
        runtimeSettings={runtimeSettings}
        saveMemory={saveMemory}
        sessionsCount={sessions.length}
        updateMemory={updateMemory}
        updateVoiceSettings={updateVoiceSettings}
        userEmail={userEmail}
        voiceSettings={voiceSettings}
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
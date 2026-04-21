import { useState } from "react";
import { AlertTriangle } from "lucide-react";

import { ArtifactsDrawer } from "@/components/caos/ArtifactsDrawer";
import { Composer } from "@/components/caos/Composer";
import { EngineChip } from "@/components/caos/EngineChip";
import { InspectorPanel } from "@/components/caos/InspectorPanel";
import { MessagePane } from "@/components/caos/MessagePane";
import { PreviousThreadsPanel } from "@/components/caos/PreviousThreadsPanel";
import { ProfileDrawer } from "@/components/caos/ProfileDrawer";
import { SwarmPanel } from "@/components/caos/SwarmPanel";
import { SearchDrawer } from "@/components/caos/SearchDrawer";
import { ShellHeader } from "@/components/caos/ShellHeader";
import { ThreadRail } from "@/components/caos/ThreadRail";
import { WelcomeHero } from "@/components/caos/WelcomeHero";
import { useCaosShell } from "@/components/caos/useCaosShell";
import "./caos-redesign.css";
import "./caos-redesign-shell.css";
import "./caos-base44-parity.css";
import "./caos-base44-parity-v2.css";


export const CaosShell = ({ authenticatedUser }) => {
  const [isRailOpen, setIsRailOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [showArtifacts, setShowArtifacts] = useState(false);
  const [showInspector, setShowInspector] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [showSwarm, setShowSwarm] = useState(false);
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
    multiAgentMode,
    searchQuery,
    saveLink,
    saveMemory,
    selectSession,
    sendMessage,
    sessions,
    setMultiAgentMode,
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
    updateProfile,
    updateVoiceSettings,
    voiceSettings,
  } = useCaosShell(authenticatedUser);
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
  const workingContextReceipt = latestReceipt || {
    active_context_tokens: 0,
    prompt_tokens: 0,
    completion_tokens: 0,
    personal_facts_count: 0,
    global_cache_count: 0,
    global_bin_status: "empty",
    wcw_budget: 200000,
  };
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
  const showWelcome = !filteredMessages.length && !draft.trim() && !busy;

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

  const handleWelcomeAction = (action) => {
    if (action === "image") {
      openArtifacts();
      return;
    }
    if (action === "models") {
      openProfile();
      return;
    }
    setDraft((current) => current || `Help me ${action.replace(/-/g, " ")}`);
  };

  return (
    <main className={`caos-shell-root ${isRailOpen ? "caos-shell-rail-open" : "caos-shell-rail-closed"}`} data-testid="caos-shell-root">
      <ShellHeader
        activeModel={runtimeSettings.default_model}
        activeProvider={runtimeSettings.default_provider}
        authenticatedUser={authenticatedUser}
        currentSession={currentSession}
        displayName={profile?.preferred_name || authenticatedUser?.name || userEmail?.split("@")[0] || "Michael"}
        isRailOpen={isRailOpen}
        onLogOut={async () => {
          try {
            await (await import("axios")).default.post(`${process.env.REACT_APP_BACKEND_URL}/api/auth/logout`, {}, { withCredentials: true });
          } catch {}
          try { localStorage.removeItem("caos_guest_mode"); } catch {}
          window.location.replace("/");
        }}
        onNewThread={() => { createSession("New Thread"); }}
        onOpenProfile={openProfile}
        onOpenSwarm={() => setShowSwarm(true)}
        onOpenThreads={toggleThreads}
        onSelectProvider={updateRuntimeSelection}
        onToggleRail={() => setIsRailOpen((value) => !value)}
        onToggleSearch={openSearch}
        providerCatalog={runtimeSettings.provider_catalog}
        wcwBudget={latestReceipt?.wcw_budget || lastTurn?.wcw_budget || 200000}
        wcwUsed={latestReceipt?.active_context_tokens || lastTurn?.wcw_used_estimate || 0}
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

          {!showWelcome ? null : null}

          {showWelcome ? (
            <WelcomeHero onCardAction={handleWelcomeAction} />
          ) : (
            <MessagePane
              busy={busy}
              currentSession={currentSession}
              messages={filteredMessages}
              onSpeak={speakText}
              receipts={artifacts.receipts}
            />
          )}
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
            <div className="command-footer-engine" data-testid="caos-command-footer-engine">
              <EngineChip
                activeModel={runtimeSettings.default_model}
                activeProvider={runtimeSettings.default_provider}
                onSelect={updateRuntimeSelection}
                providerCatalog={runtimeSettings.provider_catalog}
              />
              <button
                className={`multi-agent-toggle-chip ${multiAgentMode ? "multi-agent-toggle-chip-active" : ""}`}
                data-testid="caos-multi-agent-toggle-chip"
                onClick={() => setMultiAgentMode(!multiAgentMode)}
                title={multiAgentMode ? "Multi-Agent ON — fan out to Claude + OpenAI + Gemini" : "Click to enable Multi-Agent fan-out"}
                type="button"
              >
                <span>Multi-Agent</span>
                <strong data-testid="caos-multi-agent-toggle-state">{multiAgentMode ? "ON" : "OFF"}</strong>
              </button>
            </div>
          ) : null}
          <Composer
            busy={busy}
            draft={draft}
            lastAssistantMessage={lastAssistantMessage}
            onDraftChange={setDraft}
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
        authenticatedUser={authenticatedUser}
        isOpen={showProfile}
        memoryCount={profile?.structured_memory?.length || 0}
        onClose={() => setShowProfile(false)}
        deleteMemory={deleteMemory}
        onSpeak={speakText}
        profile={profile}
        runtimeSettings={runtimeSettings}
        saveMemory={saveMemory}
        sessionsCount={sessions.length}
        updateMemory={updateMemory}
        updateProfile={updateProfile}
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
      <SwarmPanel
        isOpen={showSwarm}
        onClose={() => setShowSwarm(false)}
      />
    </main>
  );
};
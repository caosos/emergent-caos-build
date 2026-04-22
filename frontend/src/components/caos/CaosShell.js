import { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";

import { AdminDocsDrawer } from "@/components/caos/AdminDocsDrawer";
import { ArtifactsDrawer } from "@/components/caos/ArtifactsDrawer";
import { Composer } from "@/components/caos/Composer";
import { ConstellationLayer } from "@/components/caos/ConstellationLayer";
import { EngineChip } from "@/components/caos/EngineChip";
import { InspectorPanel } from "@/components/caos/InspectorPanel";
import { MessagePane } from "@/components/caos/MessagePane";
import { PreviousThreadsPanel } from "@/components/caos/PreviousThreadsPanel";
import { ProfileDrawer } from "@/components/caos/ProfileDrawer";
import { SwarmPanel } from "@/components/caos/SwarmPanel";
import { SearchDrawer } from "@/components/caos/SearchDrawer";
import { ShellHeader } from "@/components/caos/ShellHeader";
import { SupportTicketsDrawer } from "@/components/caos/SupportTicketsDrawer";
import { WelcomeHero } from "@/components/caos/WelcomeHero";
import { useCaosShell } from "@/components/caos/useCaosShell";
import "./caos-redesign.css";
import "./caos-redesign-shell.css";
import "./caos-base44-parity.css";
import "./caos-base44-parity-v2.css";
import "./caos-base44-parity-v3.css";


export const CaosShell = ({ authenticatedUser }) => {
  const [draft, setDraft] = useState("");
  const [showAdminDocs, setShowAdminDocs] = useState(false);
  const [showSupport, setShowSupport] = useState(false);
  const [showArtifacts, setShowArtifacts] = useState(false);
  const [artifactsFilter, setArtifactsFilter] = useState("files");
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
    deleteSession,
    error,
    filteredMessages,
    files,
    lastTurn,
    links,
    multiAgentMode,
    renameSession,
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
    toggleFlagSession,
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

  const isAdmin = Boolean(profile?.is_admin || profile?.role === "admin" || authenticatedUser?.is_admin || authenticatedUser?.role === "admin");

  const [localError, setLocalError] = useState("");
  useEffect(() => {
    if (!error) { setLocalError(""); return undefined; }
    setLocalError(error);
    const timer = setTimeout(() => setLocalError(""), 5000);
    return () => clearTimeout(timer);
  }, [error]);
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

  useEffect(() => {
    const handleWheelFallback = (event) => {
      if (showArtifacts || showInspector || showProfile || showSearch || showThreadExplorer) return;
      const target = event.target;
      if (target instanceof HTMLElement && target.closest("textarea,input,select,[contenteditable='true'],.drawer-shell,.previous-threads-panel,.inspector-panel,.search-drawer")) {
        return;
      }
      const page = document.scrollingElement || document.documentElement;
      const before = page.scrollTop;
      const delta = event.deltaY;
      if (!delta || page.scrollHeight <= window.innerHeight + 4) return;
      window.requestAnimationFrame(() => {
        const after = page.scrollTop;
        if (Math.abs(after - before) > 1) return;
        page.scrollTop = Math.max(0, Math.min(page.scrollHeight, before + delta));
      });
    };
    window.addEventListener("wheel", handleWheelFallback, { passive: true, capture: true });
    return () => window.removeEventListener("wheel", handleWheelFallback, { capture: true });
  }, [showArtifacts, showInspector, showProfile, showSearch, showThreadExplorer]);

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

  const openAdminDocs = () => {
    setShowAdminDocs(true);
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
    <main className="caos-shell-root caos-shell-no-rail" data-testid="caos-shell-root">
      <ConstellationLayer />
      <ShellHeader
        activeModel={runtimeSettings.default_model}
        activeProvider={runtimeSettings.default_provider}
        authenticatedUser={authenticatedUser}
        currentSession={currentSession}
        displayName={profile?.preferred_name || authenticatedUser?.name || userEmail?.split("@")[0] || "Michael"}
        isAdmin={isAdmin}
        onLogOut={async () => {
          try {
            await (await import("axios")).default.post(`${API}/auth/logout`, {}, { withCredentials: true });
          } catch {}
          try { localStorage.removeItem("caos_guest_mode"); } catch {}
          window.location.replace("/");
        }}
        onNewThread={() => { createSession("New Thread"); }}
        onOpenAdminDocs={openAdminDocs}
        onOpenFiles={(filter) => { setArtifactsFilter(filter || "files"); setShowArtifacts(true); }}
        onOpenProfile={openProfile}
        onOpenSupport={() => setShowSupport(true)}
        onOpenSwarm={() => setShowSwarm(true)}
        onOpenThreads={toggleThreads}
        onSelectProvider={updateRuntimeSelection}
        providerCatalog={runtimeSettings.provider_catalog}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        matchCount={(searchQuery || "").trim() ? filteredMessages.reduce((count, m) => count + (String(m.content || "").toLowerCase().split(searchQuery.toLowerCase()).length - 1), 0) : 0}
        wcwBudget={latestReceipt?.wcw_budget || lastTurn?.wcw_budget || 200000}
        wcwUsed={latestReceipt?.active_context_tokens || lastTurn?.wcw_used_estimate || 0}
      />

      <div className="caos-shell-grid caos-shell-grid-layout caos-shell-grid-no-rail" data-testid="caos-shell-grid">
        <section className="caos-main-column" data-testid="caos-main-column">
          {localError ? (
            <div className="shell-error-banner" data-testid="caos-error-banner">
              <AlertTriangle size={16} />
              <span data-testid="caos-error-text">{localError}</span>
              <button
                aria-label="Dismiss error"
                className="shell-error-dismiss"
                data-testid="caos-error-banner-dismiss"
                onClick={() => setLocalError("")}
                type="button"
              >×</button>
            </div>
          ) : null}

          {showWelcome ? (
            <WelcomeHero onCardAction={handleWelcomeAction} />
          ) : (
            <MessagePane
              busy={busy}
              currentSession={currentSession}
              files={files}
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
        onDeleteSession={deleteSession}
        onFlagSession={toggleFlagSession}
        onRenameSession={renameSession}
        onSelectSession={selectSession}
        provider={runtimeSettings?.default_provider}
        sessions={sessions}
        wcwBudget={latestReceipt?.wcw_budget || lastTurn?.wcw_budget || 200000}
        wcwUsed={latestReceipt?.active_context_tokens || lastTurn?.wcw_used_estimate || 0}
      />

      <div className="command-footer" data-testid="caos-command-footer">
        <div className="command-footer-inner" data-testid="caos-command-footer-inner">
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
          <div className="composer-bottom-strip" data-testid="caos-composer-bottom-strip">
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
              title={multiAgentMode ? "Multi-Agent ON" : "Click to enable Multi-Agent fan-out"}
              type="button"
            >
              <span>Multi-Agent</span>
              <strong data-testid="caos-multi-agent-toggle-state">{multiAgentMode ? "ON" : "OFF"}</strong>
            </button>
          </div>
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
        isOpen={(searchQuery || "").trim().length > 0}
        onJumpTo={(messageId) => {
          try {
            const el = document.querySelector(`[data-testid="caos-message-bubble-${messageId}"]`);
            if (el) el.scrollIntoView({ behavior: "smooth", block: "center" });
          } catch {}
        }}
        results={filteredMessages}
        searchQuery={searchQuery}
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
        initialFilter={artifactsFilter}
        isOpen={showArtifacts}
        links={links}
        onClose={() => setShowArtifacts(false)}
        onSaveLink={saveLink}
        onUploadFile={uploadFile}
      />
      <SwarmPanel
        isOpen={showSwarm}
        onClose={() => setShowSwarm(false)}
      />
      <AdminDocsDrawer
        isOpen={showAdminDocs}
        onClose={() => setShowAdminDocs(false)}
      />
      <SupportTicketsDrawer
        isAdmin={isAdmin}
        isOpen={showSupport}
        onClose={() => setShowSupport(false)}
      />
    </main>
  );
};
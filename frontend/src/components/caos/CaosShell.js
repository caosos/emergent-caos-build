import { useEffect, useState } from "react";
import axios from "axios";
import { AlertTriangle } from "lucide-react";
import { toast } from "sonner";

import { API } from "@/config/apiBase";

import { AdminDocsDrawer } from "@/components/caos/AdminDocsDrawer";
import { AdminDashboard } from "@/components/caos/AdminDashboard";
import { ArtifactsDrawer } from "@/components/caos/ArtifactsDrawer";
import { Composer } from "@/components/caos/Composer";
import { EngineChip } from "@/components/caos/EngineChip";
import { InspectorPanel } from "@/components/caos/InspectorPanel";
import { MessagePane } from "@/components/caos/MessagePane";
import { PreviousThreadsPanel } from "@/components/caos/PreviousThreadsPanel";
import { ProfileDrawer } from "@/components/caos/ProfileDrawer";
import { ConnectorsDrawer } from "@/components/caos/ConnectorsDrawer";
import { PricingDrawer } from "@/components/caos/PricingDrawer";
import { SwarmPanel } from "@/components/caos/SwarmPanel";
import { SearchDrawer } from "@/components/caos/SearchDrawer";
import { ShellHeader } from "@/components/caos/ShellHeader";
import { SupportTicketsDrawer } from "@/components/caos/SupportTicketsDrawer";
import { WelcomeHero } from "@/components/caos/WelcomeHero";
import { VoiceFirstMode } from "@/components/caos/VoiceFirstMode";
import { useCaosShell } from "@/components/caos/useCaosShell";
import "./caos-redesign.css";
import "./caos-redesign-shell.css";
import "./caos-base44-parity.css";
import "./caos-base44-parity-v2.css";
import "./caos-base44-parity-v3.css";


export const CaosShell = ({ authenticatedUser }) => {
  const [draft, setDraft] = useState("");
  const [showAdminDocs, setShowAdminDocs] = useState(false);
  const [showAdminDashboard, setShowAdminDashboard] = useState(false);
  const [showSupport, setShowSupport] = useState(false);
  const [showArtifacts, setShowArtifacts] = useState(false);
  const [artifactsFilter, setArtifactsFilter] = useState("files");
  const [showInspector, setShowInspector] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [showConnectors, setShowConnectors] = useState(false);
  const [showPricing, setShowPricing] = useState(false);
  const [showSearch, setShowSearch] = useState(false);
  const [showSwarm, setShowSwarm] = useState(false);
  const [showThreadExplorer, setShowThreadExplorer] = useState(false);
  const [showVoiceFirst, setShowVoiceFirst] = useState(false);

  // Post-Stripe-checkout poller: when Stripe redirects back to /?caos_billing=
  // success&session_id=…, poll /billing/status/<sid> until paid, then toast +
  // refresh /billing/me. Cleans up the URL params once done so a refresh
  // doesn't re-trigger.
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const billing = params.get("caos_billing");
    const sessionId = params.get("session_id");
    if (!billing || !sessionId) return;
    if (billing === "cancel") {
      toast.error("Checkout cancelled.");
      params.delete("caos_billing"); params.delete("session_id");
      const newUrl = `${window.location.pathname}${params.toString() ? "?" + params.toString() : ""}`;
      window.history.replaceState({}, "", newUrl);
      return;
    }
    if (billing !== "success") return;
    let cancelled = false;
    const startedAt = Date.now();
    const TIMEOUT_MS = 30_000;
    const poll = async () => {
      try {
        const resp = await axios.get(`${API}/billing/status/${sessionId}`, { withCredentials: true });
        if (cancelled) return;
        if (resp.data?.status === "paid" || resp.data?.status === "already_processed") {
          toast.success(`Welcome to ${(resp.data?.tier_id || "your new tier").toUpperCase()} — pass active until ${new Date(resp.data?.tier_expires_at || Date.now()).toLocaleDateString()}`);
          params.delete("caos_billing"); params.delete("session_id");
          const newUrl = `${window.location.pathname}${params.toString() ? "?" + params.toString() : ""}`;
          window.history.replaceState({}, "", newUrl);
          return;
        }
        if (resp.data?.status === "expired" || resp.data?.status === "cancelled") {
          toast.error("Checkout session " + resp.data.status + ".");
          params.delete("caos_billing"); params.delete("session_id");
          window.history.replaceState({}, "", `${window.location.pathname}${params.toString() ? "?" + params.toString() : ""}`);
          return;
        }
        if (Date.now() - startedAt > TIMEOUT_MS) {
          toast.error("Still processing your upgrade — refresh in a moment.");
          return;
        }
        setTimeout(poll, 2000);
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn("[CAOS] billing status poll failed:", err?.message);
      }
    };
    poll();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Apply user preferences (ambient mode + bubble opacity) on boot so the
  // setting survives refresh without needing to open the Settings drawer.
  useEffect(() => {
    try {
      const ambient = localStorage.getItem("caos_ambient_mode") === "true";
      if (ambient) document.documentElement.setAttribute("data-caos-ambient", "true");
      const opacity = Number(localStorage.getItem("caos_bubble_opacity"));
      if (opacity > 0) document.documentElement.style.setProperty("--caos-bubble-opacity", String(opacity));
    } catch { /* no-op */ }
  }, []);

  // Fetch model catalog once per session so the WCW meter knows the actual
  // context window for the active engine (1 M for Claude Sonnet 4.5 / Gemini 3,
  // 400 k for GPT-5.2, etc.) instead of a hard-coded 200 k.
  const [modelSpecs, setModelSpecs] = useState(null);
  useEffect(() => {
    let cancelled = false;
    import("axios").then(({ default: axios }) => {
      import("@/config/apiBase").then(({ API }) => {
        axios.get(`${API}/caos/runtime/model-specs`)
          .then((res) => { if (!cancelled) setModelSpecs(res.data?.models || []); })
          .catch(() => { /* non-fatal — falls back to 200k */ });
      });
    });
    return () => { cancelled = true; };
  }, []);
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

  // Dynamic WCW budget — find the active model in the catalog. Fall back to
  // receipt value, then 200 k.
  const activeModelId = runtimeSettings?.default_model || "";
  const activeProviderId = runtimeSettings?.default_provider || "";
  const matchedSpec = (modelSpecs || []).find((s) => s.model === activeModelId && s.provider === activeProviderId)
    || (modelSpecs || []).find((s) => s.model === activeModelId)
    || null;
  const dynamicWcwBudget = matchedSpec?.context_window
    || latestReceipt?.wcw_budget
    || lastTurn?.wcw_budget
    || 200000;

  useEffect(() => {
    const handleWheelFallback = (event) => {
      if (showArtifacts || showInspector || showProfile || showSearch || showThreadExplorer) return;
      const target = event.target;
      if (target instanceof HTMLElement && target.closest("textarea,input,select,[contenteditable='true'],.drawer-shell,.previous-threads-panel,.inspector-panel,.search-drawer")) {
        return;
      }
      const root = document.scrollingElement || document.documentElement;
      const body = document.body;
      const page = (body?.scrollHeight || 0) > (root?.scrollHeight || 0) ? body : root;
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

  const openAdminDashboard = () => {
    setShowAdminDashboard(true);
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
      <ShellHeader
        activeModel={runtimeSettings.default_model}
        activeProvider={runtimeSettings.default_provider}
        authenticatedUser={authenticatedUser}
        currentSession={currentSession}
        displayName={profile?.preferred_name || authenticatedUser?.name || userEmail?.split("@")[0] || "Michael"}
        isAdmin={isAdmin}
        onLogOut={async () => {
          // The previous implementation used `await import("axios")` inside
          // a try/catch that silently swallowed every failure. When the user
          // clicked Log Out, the dynamic chunk fetch sometimes failed (slow
          // network, code-split race during navigation, or a midnight CDN
          // hiccup) and the catch ate the error — meaning the logout API
          // call NEVER fired AND the redirect line below was unreachable
          // because the await above never resolved nor rejected. The user
          // saw the menu close, nothing else happened, and on next
          // interaction the still-valid session_token cookie auto-restored
          // their session — i.e. "I logged out and got logged right back in."
          //
          // Fix: use the statically-imported axios + always reach the
          // redirect even if the API call fails. Worst-case the user lands
          // on the login screen and AuthGate's /auth/me probe drives the
          // final auth state. The cookie also gets a frontend-side wipe
          // (best-effort) before redirect so even if the backend Set-Cookie
          // header is lost in transit, the in-browser cookie is dead.
          let logoutOk = false;
          try {
            const resp = await axios.post(`${API}/auth/logout`, {}, { withCredentials: true });
            logoutOk = resp.status === 200;
          } catch (err) {
            // eslint-disable-next-line no-console
            console.error("[CAOS] /auth/logout call failed; forcing client-side sign-out anyway.", err);
          }
          try { localStorage.removeItem("caos_guest_mode"); } catch { /* noop */ }
          try { localStorage.removeItem("caos_assistant_named"); } catch { /* noop */ }
          // Belt-and-suspenders: nuke the cookie from the browser side too.
          // If the Set-Cookie header from the backend is dropped by an
          // intermediate proxy, this still kills the session_token locally.
          try {
            document.cookie = "session_token=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/; SameSite=None; Secure";
          } catch { /* noop */ }
          // Force a full reload (replace, not assign) so React state is
          // wiped and AuthGate's /auth/me probe fires fresh.
          if (!logoutOk) {
            // eslint-disable-next-line no-console
            console.warn("[CAOS] Logout API failed but redirecting anyway.");
          }
          window.location.replace("/");
        }}
        onNewThread={() => { createSession("New Thread"); }}
        onOpenAdminDashboard={openAdminDashboard}
        onOpenAdminDocs={openAdminDocs}
        onOpenFiles={(filter) => { setArtifactsFilter(filter || "files"); setShowArtifacts(true); }}
        onOpenInspector={() => setShowInspector(true)}
        onOpenProfile={openProfile}
        onOpenSupport={() => setShowSupport(true)}
        onOpenSwarm={() => setShowSwarm(true)}
        onOpenThreads={toggleThreads}
        onSelectProvider={updateRuntimeSelection}
        providerCatalog={runtimeSettings.provider_catalog}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        matchCount={(searchQuery || "").trim() ? filteredMessages.reduce((count, m) => count + (String(m.content || "").toLowerCase().split(searchQuery.toLowerCase()).length - 1), 0) : 0}
        wcwBudget={dynamicWcwBudget}
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
        wcwBudget={dynamicWcwBudget}
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
            <button
              className="full-voice-chip"
              data-testid="caos-full-voice-button"
              onClick={() => setShowVoiceFirst(true)}
              title="Full Voice Mode — hands-free conversation with Aria"
              type="button"
              aria-label="Enter Full Voice Mode"
            >
              <span role="img" aria-hidden="true" style={{ marginRight: 6 }}>🎙</span>
              <span>Full Voice</span>
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
        onOpenConnectors={() => { setShowProfile(false); setShowConnectors(true); }}
        onOpenPricing={() => { setShowProfile(false); setShowPricing(true); }}
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
      <ConnectorsDrawer
        isOpen={showConnectors}
        onClose={() => setShowConnectors(false)}
      />
      <PricingDrawer
        isOpen={showPricing}
        onClose={() => setShowPricing(false)}
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
      {showAdminDashboard && (
        <AdminDashboard onClose={() => setShowAdminDashboard(false)} />
      )}
      {showVoiceFirst && (
        <VoiceFirstMode
          onClose={() => setShowVoiceFirst(false)}
          onSendMessage={sendMessage}
          speakText={speakText}
          transcribeAudio={transcribeAudio}
          lastAssistantMessage={messages.filter((m) => m.role === "assistant").slice(-1)[0]}
          busy={status === "thinking" || status === "sending"}
        />
      )}
      <SupportTicketsDrawer
        isAdmin={isAdmin}
        isOpen={showSupport}
        onClose={() => setShowSupport(false)}
      />
    </main>
  );
};
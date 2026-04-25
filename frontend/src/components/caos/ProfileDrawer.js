import { useEffect, useState } from "react";
import axios from "axios";
import { Activity, AlertTriangle, Bot, Brain, Cake, Calendar, Crown, FileText, Gamepad2, Github, Image as ImageIcon, Lock, Mail, Moon, MousePointer2, Plug, Shield, Sparkles, Terminal, Trash2, Unlock, Volume2, X } from "lucide-react";
import { toast } from "sonner";

import { Switch } from "@/components/ui/switch";
import { API } from "@/config/apiBase";

import { ProfileFilesView } from "@/components/caos/ProfileFilesView";
import { ProfileMemoryView } from "@/components/caos/ProfileMemoryView";
import { VoiceSettings } from "@/components/caos/VoiceSettings";

const formatDate = (value) => {
  if (!value) return "Unknown";
  try {
    return new Date(value).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  } catch { return "Unknown"; }
};

const calculateAge = (dob) => {
  if (!dob) return null;
  try {
    const birth = new Date(dob);
    const diff = Date.now() - birth.getTime();
    return Math.floor(diff / (1000 * 60 * 60 * 24 * 365.25));
  } catch { return null; }
};

const LOCAL_KEYS = {
  remember: "caos_remember_conversations",
  gameMode: "caos_game_mode",
  devMode: "caos_developer_mode",
  multiAgent: "caos_multi_agent_mode",
  ambientMode: "caos_ambient_mode",
  scrollStep: "caos_scroll_step_px",
  bubbleOpacity: "caos_bubble_opacity",
};

const DEFAULT_SCROLL_STEP = 600;
const DEFAULT_BUBBLE_OPACITY = 0.32;

const applyAmbientMode = (enabled) => {
  const root = document.documentElement;
  if (enabled) root.setAttribute("data-caos-ambient", "true");
  else root.removeAttribute("data-caos-ambient");
};
const applyBubbleOpacity = (opacity) => {
  const pct = Math.max(0.08, Math.min(0.85, Number(opacity) || DEFAULT_BUBBLE_OPACITY));
  document.documentElement.style.setProperty("--caos-bubble-opacity", String(pct));
};

export const ProfileDrawer = ({ authenticatedUser, deleteMemory, isOpen, memoryCount, onClose, onOpenConnectors, onOpenPricing, onSpeak, profile, runtimeSettings, saveMemory, sessionsCount, updateMemory, updateProfile, updateVoiceSettings, userEmail, voiceSettings }) => {
  const [activeView, setActiveView] = useState("profile");
  const [voiceOpen, setVoiceOpen] = useState(false);
  const [memoryOpen, setMemoryOpen] = useState(false);
  const [isEditingBirthday, setIsEditingBirthday] = useState(false);
  const [birthday, setBirthday] = useState(profile?.date_of_birth || "");
  const [assistantNameDraft, setAssistantNameDraft] = useState(profile?.assistant_name || "Aria");
  const [isEditingAssistant, setIsEditingAssistant] = useState(false);
  const [toggles, setToggles] = useState({ remember: true, gameMode: false, devMode: false, multiAgent: false, ambientMode: false });
  const [githubStatus, setGithubStatus] = useState({ connected: false, masked: null });
  const [githubDraft, setGithubDraft] = useState("");
  const [githubEditing, setGithubEditing] = useState(false);
  const [githubSaving, setGithubSaving] = useState(false);
  const [scrollStep, setScrollStep] = useState(DEFAULT_SCROLL_STEP);
  const [bubbleOpacity, setBubbleOpacity] = useState(DEFAULT_BUBBLE_OPACITY);

  useEffect(() => {
    if (!isOpen) return;
    setToggles({
      remember: (localStorage.getItem(LOCAL_KEYS.remember) ?? "true") === "true",
      gameMode: localStorage.getItem(LOCAL_KEYS.gameMode) === "true",
      devMode: localStorage.getItem(LOCAL_KEYS.devMode) === "true",
      multiAgent: localStorage.getItem(LOCAL_KEYS.multiAgent) === "true",
      ambientMode: localStorage.getItem(LOCAL_KEYS.ambientMode) === "true",
    });
    setScrollStep(Number(localStorage.getItem(LOCAL_KEYS.scrollStep)) || DEFAULT_SCROLL_STEP);
    setBubbleOpacity(Number(localStorage.getItem(LOCAL_KEYS.bubbleOpacity)) || DEFAULT_BUBBLE_OPACITY);
    setBirthday(profile?.date_of_birth || "");
    setAssistantNameDraft(profile?.assistant_name || "Aria");
    setIsEditingAssistant(false);
    setActiveView("profile");
    // Fetch connector status
    axios.get(`${API}/connectors/status`)
      .then((res) => {
        const gh = (res.data || []).find((r) => r.service === "github");
        if (gh) setGithubStatus(gh);
      })
      .catch(() => { /* silent — treat as not connected */ });
  }, [isOpen, profile?.date_of_birth, profile?.assistant_name]);

  if (!isOpen) return null;

  const isAdmin = profile?.role === "admin" || profile?.is_admin === true
    || authenticatedUser?.role === "admin" || authenticatedUser?.is_admin === true;
  const displayName = profile?.preferred_name || profile?.full_name || userEmail?.split("@")[0] || "User";
  const roleLabel = isAdmin ? "Admin" : "User";

  const persistToggle = (key, value) => {
    setToggles((state) => ({ ...state, [key]: value }));
    localStorage.setItem(LOCAL_KEYS[key], String(value));
    if (key === "remember") toast.success(value ? "Memory enabled" : "Memory paused");
    if (key === "gameMode") toast.message(value ? "Game mode on" : "Game mode off");
    if (key === "devMode") toast.message(value ? "Developer mode on" : "Developer mode off");
    if (key === "multiAgent") toast.message(value ? "Multi-agent mode on" : "Multi-agent mode off");
    if (key === "ambientMode") {
      applyAmbientMode(value);
      toast.message(value ? "Ambient mode on — whispered in space" : "Ambient mode off");
    }
  };

  const persistScrollStep = (value) => {
    const next = Math.max(120, Math.min(1600, Number(value) || DEFAULT_SCROLL_STEP));
    setScrollStep(next);
    localStorage.setItem(LOCAL_KEYS.scrollStep, String(next));
  };
  const persistBubbleOpacity = (value) => {
    const next = Math.max(0.08, Math.min(0.85, Number(value) || DEFAULT_BUBBLE_OPACITY));
    setBubbleOpacity(next);
    localStorage.setItem(LOCAL_KEYS.bubbleOpacity, String(next));
    applyBubbleOpacity(next);
  };

  const saveGithubToken = async () => {
    const token = githubDraft.trim();
    if (!token) { toast.error("Paste a GitHub PAT first"); return; }
    setGithubSaving(true);
    try {
      const response = await axios.put(`${API}/connectors/github`, { token });
      setGithubStatus(response.data);
      setGithubDraft("");
      setGithubEditing(false);
      toast.success("GitHub token saved");
    } catch (error) {
      toast.error(`Save failed: ${(error.response?.data?.detail || error.message || "unknown").slice(0, 80)}`);
    } finally {
      setGithubSaving(false);
    }
  };

  const removeGithubToken = async () => {
    try {
      const response = await axios.delete(`${API}/connectors/github`);
      setGithubStatus(response.data);
      setGithubDraft("");
      setGithubEditing(false);
      toast.message("GitHub token removed");
    } catch (error) {
      toast.error(`Remove failed: ${(error.response?.data?.detail || error.message || "unknown").slice(0, 80)}`);
    }
  };

  const handleSaveBirthday = async () => {
    if (!birthday) { setIsEditingBirthday(false); return; }
    try {
      await updateProfile?.({ date_of_birth: birthday });
      toast.success("Birthday saved");
      setIsEditingBirthday(false);
    } catch (error) {
      toast.error(`Save failed: ${(error?.message || "unknown").slice(0, 60)}`);
    }
  };

  const renderHeader = () => (
    <div className="drawer-header" data-testid="caos-profile-drawer-header">
      <div className="context-card-heading">
        {activeView !== "profile" ? (
          <button className="drawer-back-button" data-testid="caos-profile-drawer-back" onClick={() => setActiveView("profile")} type="button">
            <X size={14} />
          </button>
        ) : null}
        <h2 data-testid="caos-profile-drawer-heading" style={{ textTransform: "capitalize" }}>
          {activeView === "profile" ? "Settings" : activeView}
        </h2>
      </div>
      <button className="drawer-close-button" data-testid="caos-profile-drawer-close-button" onClick={onClose} type="button">
        <X size={16} />
      </button>
    </div>
  );

  const renderProfileBody = () => (
    <div className="profile-drawer-body" data-testid="caos-profile-drawer-body">
      <div className="profile-avatar-block" data-testid="caos-profile-avatar-block">
        <div className="profile-avatar-circle" data-testid="caos-profile-avatar-circle">{displayName.charAt(0).toUpperCase()}</div>
        <strong data-testid="caos-profile-display-name">{displayName}</strong>
        <span data-testid="caos-profile-role-chip" className={`profile-role-chip ${isAdmin ? "profile-role-chip-admin" : ""}`}>{roleLabel}</span>
      </div>

      <div className="profile-tab-row" data-testid="caos-profile-tab-row">
        <button className="profile-tab-btn profile-tab-btn-files" data-testid="caos-profile-tab-files" onClick={() => setActiveView("files")} type="button">
          <FileText size={14} /><span>Files</span>
        </button>
        <button className="profile-tab-btn profile-tab-btn-photos" data-testid="caos-profile-tab-photos" onClick={() => setActiveView("photos")} type="button">
          <ImageIcon size={14} /><span>Photos</span>
        </button>
        <button className="profile-tab-btn profile-tab-btn-links" data-testid="caos-profile-tab-links" onClick={() => setActiveView("links")} type="button">
          <FileText size={14} /><span>Links</span>
        </button>
      </div>

      <div className="profile-info-block" data-testid="caos-profile-info-block">
        <div className="profile-info-row" data-testid="caos-profile-email-row">
          <Mail size={14} className="profile-info-icon profile-info-icon-blue" />
          <div><span>Email</span><strong data-testid="caos-profile-email-value">{profile?.user_email || userEmail || "—"}</strong></div>
        </div>
        <div className="profile-info-row" data-testid="caos-profile-member-row">
          <Calendar size={14} className="profile-info-icon profile-info-icon-blue" />
          <div><span>Member since</span><strong data-testid="caos-profile-member-value">{formatDate(profile?.created_date || profile?.created_at)}</strong></div>
        </div>
        <div className="profile-info-row" data-testid="caos-profile-role-row">
          <Shield size={14} className="profile-info-icon profile-info-icon-blue" />
          <div><span>Role</span><strong data-testid="caos-profile-role-value">{roleLabel}</strong></div>
        </div>
        <div className="profile-info-row profile-info-row-birthday" data-testid="caos-profile-assistant-row">
          <Bot size={14} className="profile-info-icon profile-info-icon-blue" />
          <div>
            <span>Your assistant&apos;s name</span>
            {!isEditingAssistant ? (
              <div className="profile-birthday-readonly">
                <strong data-testid="caos-profile-assistant-value">{profile?.assistant_name || "Aria"}</strong>
                <button
                  className="profile-birthday-edit"
                  data-testid="caos-profile-assistant-edit"
                  onClick={() => { setAssistantNameDraft(profile?.assistant_name || "Aria"); setIsEditingAssistant(true); }}
                  type="button"
                >Rename</button>
              </div>
            ) : (
              <div className="profile-birthday-editor">
                <input
                  className="profile-birthday-input"
                  data-testid="caos-profile-assistant-input"
                  maxLength={30}
                  onChange={(event) => setAssistantNameDraft(event.target.value)}
                  onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); event.currentTarget.blur(); } }}
                  placeholder="e.g. Nova, Axis, Luna"
                  type="text"
                  value={assistantNameDraft}
                />
                <button
                  className="profile-birthday-save"
                  data-testid="caos-profile-assistant-save"
                  onClick={async () => {
                    const trimmed = (assistantNameDraft || "").trim();
                    if (!trimmed) { setIsEditingAssistant(false); return; }
                    try {
                      await updateProfile?.({ assistant_name: trimmed });
                      toast.success(`Say hi to ${trimmed} 👋`);
                      setIsEditingAssistant(false);
                    } catch (error) {
                      toast.error(`Save failed: ${(error?.message || "unknown").slice(0, 60)}`);
                    }
                  }}
                  type="button"
                >Save</button>
                <button
                  className="profile-birthday-cancel"
                  data-testid="caos-profile-assistant-cancel"
                  onClick={() => { setAssistantNameDraft(profile?.assistant_name || "Aria"); setIsEditingAssistant(false); }}
                  type="button"
                >Cancel</button>
              </div>
            )}
          </div>
        </div>
        <div className="profile-info-row profile-info-row-birthday" data-testid="caos-profile-birthday-row">
          <Cake size={14} className="profile-info-icon profile-info-icon-blue" />
          <div>
            <span>Birthday</span>
            {!isEditingBirthday ? (
              <div className="profile-birthday-readonly">
                <strong data-testid="caos-profile-birthday-value">
                  {profile?.date_of_birth
                    ? `${formatDate(profile.date_of_birth)} (${calculateAge(profile.date_of_birth)})`
                    : "Not set"}
                </strong>
                <button className="profile-birthday-edit" data-testid="caos-profile-birthday-edit" onClick={() => setIsEditingBirthday(true)} type="button">
                  {profile?.date_of_birth ? "Edit" : "Add"}
                </button>
              </div>
            ) : (
              <div className="profile-birthday-editor">
                <input
                  className="profile-birthday-input"
                  data-testid="caos-profile-birthday-input"
                  onChange={(event) => setBirthday(event.target.value)}
                  type="date"
                  value={birthday}
                />
                <button className="profile-birthday-save" data-testid="caos-profile-birthday-save" onClick={handleSaveBirthday} type="button">Save</button>
                <button className="profile-birthday-cancel" data-testid="caos-profile-birthday-cancel" onClick={() => { setIsEditingBirthday(false); setBirthday(profile?.date_of_birth || ""); }} type="button">Cancel</button>
              </div>
            )}
          </div>
        </div>

        <button className="profile-link-row" data-testid="caos-profile-memory-link" onClick={() => setMemoryOpen(true)} type="button">
          <Brain size={14} className="profile-info-icon profile-info-icon-blue" />
          <div><span>Permanent Memories</span><strong data-testid="caos-profile-memory-count">{memoryCount} saved · View & edit</strong></div>
          <span className="profile-link-arrow">→</span>
        </button>

        <div className="profile-toggle-row" data-testid="caos-profile-toggle-remember">
          <Brain size={14} className="profile-info-icon profile-info-icon-green" />
          <div><span>Remember Conversations</span><strong>{toggles.remember ? "Enabled" : "Paused"}</strong></div>
          <Switch checked={toggles.remember} data-testid="caos-profile-toggle-remember-switch" onCheckedChange={(value) => persistToggle("remember", value)} />
        </div>

        <div className="profile-toggle-row profile-toggle-row-game" data-testid="caos-profile-toggle-game">
          <Gamepad2 size={14} className="profile-info-icon profile-info-icon-purple" />
          <div><span>Game Mode</span><strong>{isAdmin ? "Admin access" : toggles.gameMode ? "Unlocked" : "Earn tokens to unlock"}</strong></div>
          {toggles.gameMode || isAdmin ? <Unlock size={14} className="profile-toggle-lock-unlocked" /> : <Lock size={14} className="profile-toggle-lock-locked" />}
          <Switch checked={toggles.gameMode} data-testid="caos-profile-toggle-game-switch" onCheckedChange={(value) => persistToggle("gameMode", value)} />
        </div>

        {isAdmin ? (
          <>
            <div className="profile-toggle-row" data-testid="caos-profile-toggle-dev">
              <Terminal size={14} className="profile-info-icon profile-info-icon-blue" />
              <div><span>Developer Mode</span><strong>Split-screen</strong></div>
              <Switch checked={toggles.devMode} data-testid="caos-profile-toggle-dev-switch" onCheckedChange={(value) => persistToggle("devMode", value)} />
            </div>
            <div className="profile-toggle-row" data-testid="caos-profile-toggle-multi">
              <Shield size={14} className="profile-info-icon profile-info-icon-purple" />
              <div><span>Multi-Agent Mode</span><strong>Collaboration</strong></div>
              <Switch checked={toggles.multiAgent} data-testid="caos-profile-toggle-multi-switch" onCheckedChange={(value) => persistToggle("multiAgent", value)} />
            </div>
            <button className="profile-link-row profile-link-row-console" data-testid="caos-profile-console-link" onClick={() => toast.message("System Console — coming in Phase 4 (OS Layer)")} type="button">
              <Activity size={14} className="profile-info-icon profile-info-icon-cyan" />
              <div><span>System Console</span><strong>Monitor metrics</strong></div>
            </button>
          </>
        ) : null}

        <div className="profile-chat-mode-row" data-testid="caos-profile-chat-mode-row">
          <Activity size={14} className="profile-info-icon profile-info-icon-cyan" />
          <div style={{ flex: 1, minWidth: 0 }}>
            <span>Aria Mode</span>
            <strong>{(profile?.chat_mode || "balanced").replace(/^./, (c) => c.toUpperCase())} · {({ fact: "temp 0.1", balanced: "temp 0.3", creative: "temp 0.7" })[profile?.chat_mode || "balanced"]}</strong>
          </div>
          <div className="profile-chat-mode-buttons" data-testid="caos-profile-chat-mode-buttons">
            {["fact", "balanced", "creative"].map((mode) => {
              const active = (profile?.chat_mode || "balanced") === mode;
              return (
                <button
                  key={mode}
                  type="button"
                  data-testid={`caos-profile-chat-mode-${mode}`}
                  className={`profile-chat-mode-btn ${active ? "profile-chat-mode-btn-active" : ""}`}
                  onClick={async () => {
                    if (active) return;
                    try {
                      await updateProfile?.({ chat_mode: mode });
                      toast.success(`Aria set to ${mode} mode`);
                    } catch (error) {
                      toast.error(`Save failed: ${(error?.message || "unknown").slice(0, 60)}`);
                    }
                  }}
                >{mode[0].toUpperCase()}</button>
              );
            })}
          </div>
        </div>

        <button className="profile-voice-row" data-testid="caos-profile-voice-link" onClick={() => setVoiceOpen(true)} type="button">
          <Volume2 size={14} className="profile-info-icon profile-info-icon-purple" />
          <div><span>Voice & Speech</span><strong>{voiceSettings?.tts_voice || "nova"} · {(voiceSettings?.tts_speed || 1.0).toFixed(2)}×</strong></div>
          <span className="profile-link-arrow">→</span>
        </button>

        {/* Ambient mode — per-user transparent chat aesthetic */}
        <div className="profile-toggle-row" data-testid="caos-profile-toggle-ambient">
          <Moon size={14} className="profile-info-icon profile-info-icon-purple" />
          <div><span>Ambient Mode</span><strong>{toggles.ambientMode ? "Whispered in space" : "Standard bubbles"}</strong></div>
          <Switch checked={toggles.ambientMode} data-testid="caos-profile-toggle-ambient-switch" onCheckedChange={(value) => persistToggle("ambientMode", value)} />
        </div>

        {/* Scroll step slider */}
        <div className="profile-slider-row" data-testid="caos-profile-scroll-step-row">
          <MousePointer2 size={14} className="profile-info-icon profile-info-icon-cyan" />
          <div style={{ flex: 1, minWidth: 0 }}>
            <span>Scroll step</span>
            <strong>{scrollStep}px per click</strong>
          </div>
          <input
            className="profile-slider-input"
            data-testid="caos-profile-scroll-step-slider"
            type="range"
            min={200}
            max={1400}
            step={40}
            value={scrollStep}
            onChange={(event) => persistScrollStep(event.target.value)}
          />
        </div>

        {/* Bubble opacity slider */}
        <div className="profile-slider-row" data-testid="caos-profile-bubble-opacity-row">
          <Sparkles size={14} className="profile-info-icon profile-info-icon-purple" />
          <div style={{ flex: 1, minWidth: 0 }}>
            <span>Bubble transparency</span>
            <strong>{Math.round((1 - bubbleOpacity) * 100)}% see-through</strong>
          </div>
          <input
            className="profile-slider-input"
            data-testid="caos-profile-bubble-opacity-slider"
            type="range"
            min={0.08}
            max={0.85}
            step={0.02}
            value={bubbleOpacity}
            onChange={(event) => persistBubbleOpacity(event.target.value)}
          />
        </div>

        {/* Connectors hub — replaces the previous GitHub-only PAT row. The
            new drawer (`<ConnectorsDrawer />`) handles all providers (Google,
            GitHub, MCP coming) in one place; this button opens it. */}
        <button
          className="profile-connector-row"
          data-testid="caos-profile-open-connectors"
          onClick={() => { try { onClose?.(); } catch {} onOpenConnectors?.(); }}
          type="button"
          style={{ width: "100%", cursor: "pointer", textAlign: "left", background: "transparent", border: "none", padding: 0 }}
        >
          <Plug size={14} className="profile-info-icon" />
          <div style={{ flex: 1, minWidth: 0 }}>
            <span>Connectors</span>
            <strong data-testid="caos-profile-connectors-summary">
              Gmail · Drive · Docs · Calendar · GitHub · Slack · Twilio · Telegram · MCP →
            </strong>
          </div>
          <span className="profile-connector-action" style={{ pointerEvents: "none" }}>Open</span>
        </button>

        {/* Pricing & tier upgrade */}
        <button
          className="profile-connector-row"
          data-testid="caos-profile-open-pricing"
          onClick={() => { try { onClose?.(); } catch {} onOpenPricing?.(); }}
          type="button"
          style={{ width: "100%", cursor: "pointer", textAlign: "left", background: "transparent", border: "none", padding: 0 }}
        >
          <Crown size={14} className="profile-info-icon" />
          <div style={{ flex: 1, minWidth: 0 }}>
            <span>Pricing & Tiers</span>
            <strong data-testid="caos-profile-pricing-summary">
              Upgrade for more daily tokens · 30-day passes →
            </strong>
          </div>
          <span className="profile-connector-action" style={{ pointerEvents: "none" }}>Open</span>
        </button>

        <button
          className="profile-danger-row"
          data-testid="caos-profile-delete-account"
          onClick={() => toast.error("Account deletion not wired yet — contact admin to remove.")}
          type="button"
        >
          <Trash2 size={14} /><span>Delete Account</span>
        </button>
      </div>
    </div>
  );

  return (
    <>
      <div className="drawer-overlay" data-testid="caos-profile-drawer-overlay" onClick={onClose}>
        <aside className="drawer-shell" data-testid="caos-profile-drawer" onClick={(event) => event.stopPropagation()}>
          {renderHeader()}
          {activeView === "profile" ? renderProfileBody() : null}
          {activeView === "files" || activeView === "photos" || activeView === "links" ? (
            <ProfileFilesView kind={activeView} profile={profile} userEmail={userEmail} />
          ) : null}
        </aside>
      </div>
      <VoiceSettings
        isOpen={voiceOpen}
        onClose={() => setVoiceOpen(false)}
        onSave={updateVoiceSettings}
        onSpeak={onSpeak}
        voiceSettings={voiceSettings}
      />
      <ProfileMemoryView
        deleteMemory={deleteMemory}
        isOpen={memoryOpen}
        memories={profile?.structured_memory || []}
        onClose={() => setMemoryOpen(false)}
        saveMemory={saveMemory}
        updateMemory={updateMemory}
      />
    </>
  );
};

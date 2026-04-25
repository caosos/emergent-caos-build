import { useEffect, useState, useCallback, useRef } from "react";
import axios from "axios";
import { Github, X, Mail, FolderOpen, FileText, Calendar, Sparkles, Upload, BookOpen, Plus, Trash2, MessageSquare, Phone, Send } from "lucide-react";
import { toast } from "sonner";

import { API } from "@/config/apiBase";
import "@/components/caos/connectors.css";
import { openOAuthPopup, buildGoogleConnectorsRedirectUri } from "@/components/caos/connector-popup-handler";

/**
 * ConnectorsDrawer — single hub the user opens from Profile → Connectors.
 *
 * Renders one card per supported provider. Each card is responsible for its
 * own connect/disconnect/reauth actions; the drawer is a pure layout shell.
 *
 * Backend API:
 *   GET  /api/connectors/list                     → ConnectorState[]
 *   POST /api/connectors/google/start             → { auth_url, state }
 *   POST /api/connectors/google/callback          → forwarded by popup
 *   POST /api/connectors/google/disconnect        → revoke + delete
 *   PUT  /api/connectors/github { token }         → store PAT (legacy shape)
 *   DELETE /api/connectors/github                 → remove PAT
 */

const PROVIDER_VISUALS = {
  google: {
    icon: <Mail size={18} />,
    blurb: "One consent unlocks Gmail, Drive, Docs, and Calendar (read-only). Aria can summarize your inbox, find files, and read your schedule.",
    capabilities: [
      { icon: <Mail size={11} />, label: "Gmail" },
      { icon: <FolderOpen size={11} />, label: "Drive" },
      { icon: <FileText size={11} />, label: "Docs" },
      { icon: <Calendar size={11} />, label: "Calendar" },
    ],
  },
  github: {
    icon: <Github size={18} />,
    blurb: "Paste a Personal Access Token (PAT) to let Aria read your private repos. Public repos work without a token.",
    capabilities: [
      { icon: <Github size={11} />, label: "Read repos" },
    ],
  },
  mcp: {
    icon: <Sparkles size={18} />,
    blurb: "Connect ANY MCP server (Notion, Linear, Stripe, Sentry, custom). One protocol, infinite reach. Add server URL + optional auth header below.",
    capabilities: [],
  },
  obsidian: {
    icon: <BookOpen size={18} />,
    blurb: "Upload your Obsidian vault folder (only .md files are read). Aria can search notes, follow wikilinks, and trace backlinks. Re-upload to refresh.",
    capabilities: [
      { icon: <BookOpen size={11} />, label: "Notes" },
      { icon: <FileText size={11} />, label: "Backlinks" },
    ],
  },
  slack: {
    icon: <MessageSquare size={18} />,
    blurb: "Paste a Slack bot token (xoxb-…). Aria can list channels, search messages (xoxp- only), and post with your approval.",
    capabilities: [
      { icon: <MessageSquare size={11} />, label: "Channels" },
      { icon: <Send size={11} />, label: "Post (gated)" },
    ],
  },
  twilio: {
    icon: <Phone size={18} />,
    blurb: "Wire Twilio for outbound SMS. Need Account SID + Auth Token + an SMS-enabled From-number from your Twilio console.",
    capabilities: [
      { icon: <Phone size={11} />, label: "SMS send (gated)" },
    ],
  },
  telegram: {
    icon: <Send size={18} />,
    blurb: "Paste your Telegram bot token (from @BotFather). Aria can send messages to any chat the bot has access to (with your approval).",
    capabilities: [
      { icon: <Send size={11} />, label: "Bot send (gated)" },
    ],
  },
};

const StatusPill = ({ state }) => {
  let tone = "default";
  let text = "Not connected";
  if (state.needs_reauth) { tone = "needs-reauth"; text = "Needs reauth"; }
  else if (state.connected) {
    tone = "connected";
    text = state.masked_identity ? `Connected · ${state.masked_identity}` : "Connected";
  }
  if (state.last_error && !state.connected) { tone = "error"; text = state.last_error.slice(0, 80); }
  return <div className="connector-card-status" data-tone={tone}>{text}</div>;
};

// ── Google card ────────────────────────────────────────────────────────────

const GoogleCard = ({ state, onChanged }) => {
  const [busy, setBusy] = useState(false);
  const visuals = PROVIDER_VISUALS.google;

  const connect = async () => {
    setBusy(true);
    try {
      const redirectUri = buildGoogleConnectorsRedirectUri();
      // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS,
      // THIS BREAKS THE AUTH.
      const startResp = await axios.post(
        `${API}/connectors/google/start`,
        { redirect_uri: redirectUri },
        { withCredentials: true },
      );
      const authUrl = startResp.data?.auth_url;
      if (!authUrl) throw new Error("Backend did not return a Google consent URL.");
      const result = await openOAuthPopup(authUrl, "caos_google_oauth");
      toast.success(`Google connected as ${result.email || "your account"}`);
      onChanged?.();
    } catch (err) {
      toast.error(err?.message || "Google connection failed");
    } finally {
      setBusy(false);
    }
  };

  const disconnect = async () => {
    if (!window.confirm("Disconnect Google? Aria will lose access to Gmail/Drive/Docs/Calendar.")) return;
    setBusy(true);
    try {
      await axios.post(`${API}/connectors/google/disconnect`, {}, { withCredentials: true });
      toast.success("Google disconnected");
      onChanged?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || err?.message || "Disconnect failed");
    } finally {
      setBusy(false);
    }
  };

  const cardState = state.needs_reauth ? "needs-reauth" : state.connected ? "connected" : "not-connected";

  return (
    <div className="connector-card" data-state={cardState} data-testid="caos-connector-card-google">
      <div className="connector-card-head">
        <div className="connector-card-icon">{visuals.icon}</div>
        <div className="connector-card-meta">
          <div className="connector-card-name">Google Workspace</div>
          <StatusPill state={state} />
        </div>
      </div>
      <div className="connector-card-body">
        {visuals.blurb}
        {visuals.capabilities.length ? (
          <div style={{ display: "flex", gap: 8, marginTop: 6, flexWrap: "wrap" }}>
            {visuals.capabilities.map((cap) => (
              <span key={cap.label} style={{
                display: "inline-flex", alignItems: "center", gap: 4,
                padding: "2px 8px", borderRadius: 999,
                background: "rgba(167,139,250,0.12)", color: "#c4b5fd", fontSize: 10.5,
              }}>{cap.icon}{cap.label}</span>
            ))}
          </div>
        ) : null}
      </div>
      <div className="connector-card-actions">
        {!state.connected || state.needs_reauth ? (
          <button
            className="connector-action-btn"
            data-variant="primary"
            data-testid="caos-connector-card-google-connect"
            disabled={busy}
            onClick={connect}
            type="button"
          >{busy ? "Opening Google…" : state.needs_reauth ? "Reconnect" : "Connect Google"}</button>
        ) : (
          <button
            className="connector-action-btn"
            data-variant="danger"
            data-testid="caos-connector-card-google-disconnect"
            disabled={busy}
            onClick={disconnect}
            type="button"
          >{busy ? "Disconnecting…" : "Disconnect"}</button>
        )}
      </div>
    </div>
  );
};

// ── GitHub card (PAT-based, legacy storage shape preserved) ────────────────

const GitHubCard = ({ state, onChanged }) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const visuals = PROVIDER_VISUALS.github;

  const save = async () => {
    const token = draft.trim();
    if (!token || token.length < 8) { toast.error("Paste a valid GitHub PAT first"); return; }
    setBusy(true);
    try {
      await axios.put(`${API}/connectors/github`, { token }, { withCredentials: true });
      toast.success("GitHub PAT saved");
      setEditing(false);
      setDraft("");
      onChanged?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || err?.message || "Save failed");
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!window.confirm("Remove GitHub PAT? Aria will lose access to your private repos.")) return;
    setBusy(true);
    try {
      await axios.delete(`${API}/connectors/github`, { withCredentials: true });
      toast.success("GitHub PAT removed");
      onChanged?.();
    } catch (err) {
      toast.error(err?.message || "Remove failed");
    } finally {
      setBusy(false);
    }
  };

  const cardState = state.connected ? "connected" : "not-connected";

  return (
    <div className="connector-card" data-state={cardState} data-testid="caos-connector-card-github">
      <div className="connector-card-head">
        <div className="connector-card-icon">{visuals.icon}</div>
        <div className="connector-card-meta">
          <div className="connector-card-name">GitHub</div>
          <StatusPill state={state} />
        </div>
      </div>
      <div className="connector-card-body">{visuals.blurb}</div>
      <div className="connector-card-actions">
        {!editing ? (
          <>
            <button
              className="connector-action-btn"
              data-variant={state.connected ? "ghost" : "primary"}
              data-testid="caos-connector-card-github-toggle"
              disabled={busy}
              onClick={() => { setDraft(""); setEditing(true); }}
              type="button"
            >{state.connected ? "Rotate token" : "Connect GitHub"}</button>
            {state.connected ? (
              <button
                className="connector-action-btn"
                data-variant="danger"
                data-testid="caos-connector-card-github-remove"
                disabled={busy}
                onClick={remove}
                type="button"
              >{busy ? "Removing…" : "Disconnect"}</button>
            ) : null}
          </>
        ) : (
          <>
            <input
              autoFocus
              className="connector-pat-input"
              data-testid="caos-connector-card-github-input"
              type="password"
              placeholder="ghp_… or github_pat_…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") save();
                if (e.key === "Escape") { setEditing(false); setDraft(""); }
              }}
            />
            <button
              className="connector-action-btn"
              data-variant="primary"
              data-testid="caos-connector-card-github-save"
              disabled={busy}
              onClick={save}
              type="button"
            >{busy ? "Saving…" : "Save"}</button>
            <button
              className="connector-action-btn"
              data-variant="ghost"
              data-testid="caos-connector-card-github-cancel"
              onClick={() => { setEditing(false); setDraft(""); }}
              type="button"
            >Cancel</button>
          </>
        )}
      </div>
    </div>
  );
};

// ── Obsidian card (vault upload) ───────────────────────────────────────────

const ObsidianCard = ({ state, onChanged }) => {
  const [busy, setBusy] = useState(false);
  const fileInputRef = useRef(null);
  const visuals = PROVIDER_VISUALS.obsidian;

  const onPickFolder = () => fileInputRef.current?.click();

  const onFiles = async (event) => {
    const fileList = Array.from(event.target.files || []);
    const mdFiles = fileList.filter((f) => f.name.toLowerCase().endsWith(".md"));
    if (!mdFiles.length) {
      toast.error("No .md files found in that folder.");
      return;
    }
    setBusy(true);
    const status = toast.loading(`Reading ${mdFiles.length} notes…`);
    try {
      const notes = [];
      for (const file of mdFiles) {
        // webkitRelativePath gives us the vault-relative path for free.
        const path = file.webkitRelativePath || file.name;
        const content = await file.text();
        notes.push({ path, content });
      }
      const resp = await axios.post(
        `${API}/connectors/obsidian/upload`,
        { notes },
        { withCredentials: true },
      );
      toast.dismiss(status);
      toast.success(`Indexed ${resp.data.note_count} notes (${resp.data.tag_count} tags).`);
      onChanged?.();
    } catch (err) {
      toast.dismiss(status);
      toast.error(err?.response?.data?.detail || err?.message || "Vault upload failed.");
    } finally {
      setBusy(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const onDisconnect = async () => {
    if (!window.confirm("Delete the indexed Obsidian vault? Aria will lose access until you upload again.")) return;
    setBusy(true);
    try {
      await axios.delete(`${API}/connectors/obsidian`, { withCredentials: true });
      toast.success("Obsidian vault removed.");
      onChanged?.();
    } catch (err) {
      toast.error(err?.message || "Remove failed.");
    } finally {
      setBusy(false);
    }
  };

  const cardState = state.connected ? "connected" : "not-connected";

  return (
    <div className="connector-card" data-state={cardState} data-testid="caos-connector-card-obsidian">
      <div className="connector-card-head">
        <div className="connector-card-icon">{visuals.icon}</div>
        <div className="connector-card-meta">
          <div className="connector-card-name">Obsidian</div>
          <StatusPill state={state} />
        </div>
      </div>
      <div className="connector-card-body">{visuals.blurb}</div>
      <div className="connector-card-actions">
        <input
          ref={fileInputRef}
          type="file"
          // webkitdirectory lets the user pick a whole vault folder.
          webkitdirectory=""
          directory=""
          multiple
          style={{ display: "none" }}
          onChange={onFiles}
          data-testid="caos-connector-card-obsidian-input"
        />
        <button
          className="connector-action-btn"
          data-variant="primary"
          data-testid="caos-connector-card-obsidian-upload"
          onClick={onPickFolder}
          disabled={busy}
          type="button"
        >
          <Upload size={11} style={{ display: "inline", marginRight: 4 }} />
          {busy ? "Indexing…" : state.connected ? "Re-upload vault" : "Upload vault folder"}
        </button>
        {state.connected ? (
          <button
            className="connector-action-btn"
            data-variant="danger"
            data-testid="caos-connector-card-obsidian-disconnect"
            onClick={onDisconnect}
            disabled={busy}
            type="button"
          >Remove</button>
        ) : null}
      </div>
    </div>
  );
};

// ── Slack card (bot-token PAT) ─────────────────────────────────────────────

const SlackCard = ({ state, onChanged }) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const visuals = PROVIDER_VISUALS.slack;

  const save = async () => {
    const token = draft.trim();
    if (!token.startsWith("xoxb-") && !token.startsWith("xoxp-")) {
      toast.error("Token should start with xoxb- (bot) or xoxp- (user)."); return;
    }
    setBusy(true);
    try {
      await axios.put(`${API}/connectors/slack`, { token }, { withCredentials: true });
      toast.success("Slack token saved");
      setEditing(false); setDraft("");
      onChanged?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || err?.message || "Save failed");
    } finally { setBusy(false); }
  };

  const remove = async () => {
    if (!window.confirm("Remove Slack token? Aria loses access.")) return;
    setBusy(true);
    try {
      await axios.delete(`${API}/connectors/slack`, { withCredentials: true });
      toast.success("Slack disconnected");
      onChanged?.();
    } catch (err) { toast.error(err?.message || "Remove failed"); }
    finally { setBusy(false); }
  };

  const cardState = state.connected ? "connected" : "not-connected";
  return (
    <div className="connector-card" data-state={cardState} data-testid="caos-connector-card-slack">
      <div className="connector-card-head">
        <div className="connector-card-icon">{visuals.icon}</div>
        <div className="connector-card-meta">
          <div className="connector-card-name">Slack</div>
          <StatusPill state={state} />
        </div>
      </div>
      <div className="connector-card-body">{visuals.blurb}</div>
      <div className="connector-card-actions">
        {!editing ? (
          <>
            <button
              className="connector-action-btn"
              data-variant={state.connected ? "ghost" : "primary"}
              data-testid="caos-connector-card-slack-toggle"
              disabled={busy}
              onClick={() => { setDraft(""); setEditing(true); }}
              type="button"
            >{state.connected ? "Rotate token" : "Connect Slack"}</button>
            {state.connected ? (
              <button className="connector-action-btn" data-variant="danger" data-testid="caos-connector-card-slack-remove" disabled={busy} onClick={remove} type="button">
                {busy ? "Removing…" : "Disconnect"}
              </button>
            ) : null}
          </>
        ) : (
          <>
            <input
              autoFocus
              className="connector-pat-input"
              data-testid="caos-connector-card-slack-input"
              type="password"
              placeholder="xoxb-… or xoxp-…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") save(); if (e.key === "Escape") { setEditing(false); setDraft(""); } }}
            />
            <button className="connector-action-btn" data-variant="primary" disabled={busy} onClick={save} type="button">{busy ? "Saving…" : "Save"}</button>
            <button className="connector-action-btn" data-variant="ghost" onClick={() => { setEditing(false); setDraft(""); }} type="button">Cancel</button>
          </>
        )}
      </div>
    </div>
  );
};

// ── Twilio card (multi-field) ──────────────────────────────────────────────

const TwilioCard = ({ state, onChanged }) => {
  const [editing, setEditing] = useState(false);
  const [sid, setSid] = useState("");
  const [auth, setAuth] = useState("");
  const [from, setFrom] = useState("");
  const [busy, setBusy] = useState(false);
  const visuals = PROVIDER_VISUALS.twilio;

  const save = async () => {
    if (!sid.trim() || !auth.trim() || !from.trim()) { toast.error("All three fields required"); return; }
    setBusy(true);
    try {
      await axios.put(
        `${API}/connectors/twilio`,
        { account_sid: sid.trim(), auth_token: auth.trim(), from_number: from.trim() },
        { withCredentials: true },
      );
      toast.success("Twilio connected");
      setEditing(false); setSid(""); setAuth(""); setFrom("");
      onChanged?.();
    } catch (err) { toast.error(err?.response?.data?.detail || err?.message || "Save failed"); }
    finally { setBusy(false); }
  };

  const remove = async () => {
    if (!window.confirm("Remove Twilio credentials?")) return;
    try {
      await axios.delete(`${API}/connectors/twilio`, { withCredentials: true });
      toast.success("Twilio disconnected");
      onChanged?.();
    } catch (err) { toast.error(err?.message || "Remove failed"); }
  };

  const cardState = state.connected ? "connected" : "not-connected";
  return (
    <div className="connector-card" data-state={cardState} data-testid="caos-connector-card-twilio">
      <div className="connector-card-head">
        <div className="connector-card-icon">{visuals.icon}</div>
        <div className="connector-card-meta">
          <div className="connector-card-name">Twilio SMS</div>
          <StatusPill state={state} />
        </div>
      </div>
      <div className="connector-card-body">{visuals.blurb}</div>
      <div className="connector-card-actions">
        {!editing ? (
          <>
            <button className="connector-action-btn" data-variant={state.connected ? "ghost" : "primary"} data-testid="caos-connector-card-twilio-toggle" disabled={busy} onClick={() => setEditing(true)} type="button">
              {state.connected ? "Update credentials" : "Connect Twilio"}
            </button>
            {state.connected ? (
              <button className="connector-action-btn" data-variant="danger" onClick={remove} type="button">Disconnect</button>
            ) : null}
          </>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 6, width: "100%" }}>
            <input className="connector-pat-input" data-testid="caos-connector-card-twilio-sid" placeholder="Account SID (AC…)" value={sid} onChange={(e) => setSid(e.target.value)} />
            <input className="connector-pat-input" data-testid="caos-connector-card-twilio-auth" type="password" placeholder="Auth Token" value={auth} onChange={(e) => setAuth(e.target.value)} />
            <input className="connector-pat-input" data-testid="caos-connector-card-twilio-from" placeholder="From-number (e.g. +15551234567)" value={from} onChange={(e) => setFrom(e.target.value)} />
            <div style={{ display: "flex", gap: 8 }}>
              <button className="connector-action-btn" data-variant="primary" disabled={busy} onClick={save} type="button">{busy ? "Saving…" : "Save"}</button>
              <button className="connector-action-btn" data-variant="ghost" onClick={() => { setEditing(false); setSid(""); setAuth(""); setFrom(""); }} type="button">Cancel</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// ── Telegram card (single bot_token field) ─────────────────────────────────

const TelegramCard = ({ state, onChanged }) => {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const visuals = PROVIDER_VISUALS.telegram;

  const save = async () => {
    const token = draft.trim();
    if (!token.includes(":")) { toast.error("Telegram bot tokens look like 12345:abc…"); return; }
    setBusy(true);
    try {
      await axios.put(`${API}/connectors/telegram`, { bot_token: token }, { withCredentials: true });
      toast.success("Telegram bot connected");
      setEditing(false); setDraft("");
      onChanged?.();
    } catch (err) { toast.error(err?.response?.data?.detail || err?.message || "Save failed"); }
    finally { setBusy(false); }
  };

  const remove = async () => {
    if (!window.confirm("Remove Telegram bot token?")) return;
    try {
      await axios.delete(`${API}/connectors/telegram`, { withCredentials: true });
      toast.success("Telegram disconnected");
      onChanged?.();
    } catch (err) { toast.error(err?.message || "Remove failed"); }
  };

  const cardState = state.connected ? "connected" : "not-connected";
  return (
    <div className="connector-card" data-state={cardState} data-testid="caos-connector-card-telegram">
      <div className="connector-card-head">
        <div className="connector-card-icon">{visuals.icon}</div>
        <div className="connector-card-meta">
          <div className="connector-card-name">Telegram</div>
          <StatusPill state={state} />
        </div>
      </div>
      <div className="connector-card-body">{visuals.blurb}</div>
      <div className="connector-card-actions">
        {!editing ? (
          <>
            <button className="connector-action-btn" data-variant={state.connected ? "ghost" : "primary"} data-testid="caos-connector-card-telegram-toggle" disabled={busy} onClick={() => { setDraft(""); setEditing(true); }} type="button">
              {state.connected ? "Rotate token" : "Connect Telegram"}
            </button>
            {state.connected ? (
              <button className="connector-action-btn" data-variant="danger" onClick={remove} type="button">Disconnect</button>
            ) : null}
          </>
        ) : (
          <>
            <input
              autoFocus
              className="connector-pat-input"
              data-testid="caos-connector-card-telegram-input"
              type="password"
              placeholder="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") save(); if (e.key === "Escape") { setEditing(false); setDraft(""); } }}
            />
            <button className="connector-action-btn" data-variant="primary" disabled={busy} onClick={save} type="button">{busy ? "Saving…" : "Save"}</button>
            <button className="connector-action-btn" data-variant="ghost" onClick={() => { setEditing(false); setDraft(""); }} type="button">Cancel</button>
          </>
        )}
      </div>
    </div>
  );
};

// ── MCP card (server registry, real CRUD) ──────────────────────────────────

const McpCard = ({ state, onChanged }) => {
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [authHeader, setAuthHeader] = useState("");
  const [busy, setBusy] = useState(false);
  const [servers, setServers] = useState([]);
  const visuals = PROVIDER_VISUALS.mcp;

  const refreshServers = useCallback(async () => {
    try {
      const resp = await axios.get(`${API}/connectors/mcp/list`, { withCredentials: true });
      setServers(Array.isArray(resp.data) ? resp.data : []);
    } catch (err) {
      // silent — empty list is fine
    }
  }, []);

  useEffect(() => { refreshServers(); }, [refreshServers, state.connected]);

  const onAdd = async () => {
    if (!name.trim() || !url.trim()) {
      toast.error("Name and URL required.");
      return;
    }
    setBusy(true);
    try {
      const resp = await axios.post(
        `${API}/connectors/mcp/add`,
        { name: name.trim(), url: url.trim(), auth_header: authHeader.trim() || null },
        { withCredentials: true },
      );
      toast.success(`Added ${resp.data.name} (${(resp.data.tools || []).length} tools)`);
      setName(""); setUrl(""); setAuthHeader(""); setAdding(false);
      await refreshServers();
      onChanged?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || err?.message || "Add failed");
    } finally {
      setBusy(false);
    }
  };

  const onDelete = async (serverId) => {
    if (!window.confirm("Disconnect this MCP server?")) return;
    try {
      await axios.delete(`${API}/connectors/mcp/${serverId}`, { withCredentials: true });
      toast.success("MCP server removed.");
      await refreshServers();
      onChanged?.();
    } catch (err) {
      toast.error(err?.message || "Remove failed.");
    }
  };

  const cardState = servers.length ? "connected" : "not-connected";

  return (
    <div className="connector-card" data-state={cardState} data-testid="caos-connector-card-mcp">
      <div className="connector-card-head">
        <div className="connector-card-icon">{visuals.icon}</div>
        <div className="connector-card-meta">
          <div className="connector-card-name">MCP Servers</div>
          <div className="connector-card-status" data-tone={servers.length ? "connected" : "default"}>
            {servers.length ? `${servers.length} server(s) connected` : "No servers yet"}
          </div>
        </div>
      </div>
      <div className="connector-card-body">{visuals.blurb}</div>

      {servers.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }} data-testid="caos-mcp-server-list">
          {servers.map((srv) => (
            <div
              key={srv.server_id}
              data-testid={`caos-mcp-server-${srv.server_id}`}
              style={{
                display: "flex", alignItems: "center", gap: 8,
                padding: "6px 10px", borderRadius: 8,
                background: "rgba(0,0,0,0.28)", border: "1px solid rgba(167,139,250,0.16)",
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12.5, color: "#e2e8f0", fontWeight: 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {srv.name}
                </div>
                <div style={{ fontSize: 10.5, color: "rgba(226,232,240,0.5)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                  {(srv.tools_cache || []).length} tool(s) · {srv.url}
                </div>
                {srv.last_error ? (
                  <div style={{ fontSize: 10.5, color: "rgba(252,165,165,0.92)", marginTop: 2 }}>
                    error: {srv.last_error.slice(0, 80)}
                  </div>
                ) : null}
              </div>
              <button
                className="connector-action-btn"
                data-variant="danger"
                style={{ padding: "4px 8px", fontSize: 11 }}
                onClick={() => onDelete(srv.server_id)}
                title="Remove this MCP server"
                type="button"
              ><Trash2 size={11} /></button>
            </div>
          ))}
        </div>
      ) : null}

      <div className="connector-card-actions">
        {!adding ? (
          <button
            className="connector-action-btn"
            data-variant="primary"
            data-testid="caos-connector-card-mcp-add-toggle"
            onClick={() => setAdding(true)}
            type="button"
          ><Plus size={11} style={{ display: "inline", marginRight: 4 }} />Add MCP server</button>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 6, width: "100%" }}>
            <input
              autoFocus
              className="connector-pat-input"
              placeholder="Display name (e.g. Notion)"
              value={name}
              onChange={(e) => setName(e.target.value)}
              data-testid="caos-mcp-add-name"
            />
            <input
              className="connector-pat-input"
              placeholder="https://server.example.com/mcp"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              data-testid="caos-mcp-add-url"
            />
            <input
              className="connector-pat-input"
              type="password"
              placeholder="Auth header (optional, e.g. 'Bearer xyz')"
              value={authHeader}
              onChange={(e) => setAuthHeader(e.target.value)}
              data-testid="caos-mcp-add-auth"
            />
            <div style={{ display: "flex", gap: 8 }}>
              <button
                className="connector-action-btn"
                data-variant="primary"
                data-testid="caos-mcp-add-save"
                onClick={onAdd}
                disabled={busy}
                type="button"
              >{busy ? "Connecting…" : "Connect"}</button>
              <button
                className="connector-action-btn"
                data-variant="ghost"
                onClick={() => { setAdding(false); setName(""); setUrl(""); setAuthHeader(""); }}
                type="button"
              >Cancel</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

// ── Drawer shell ───────────────────────────────────────────────────────────

export const ConnectorsDrawer = ({ isOpen, onClose }) => {
  const [states, setStates] = useState([]);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await axios.get(`${API}/connectors/list`, { withCredentials: true });
      setStates(Array.isArray(resp.data) ? resp.data : []);
    } catch (err) {
      toast.error(err?.response?.data?.detail || err?.message || "Connector status failed");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isOpen) refresh();
  }, [isOpen, refresh]);

  if (!isOpen) return null;

  const byProvider = (key) =>
    states.find((s) => s.provider === key) || { provider: key, label: key, connected: false };

  return (
    <div
      className="drawer-overlay"
      data-testid="caos-connectors-drawer-overlay"
      onClick={onClose}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 219 }}
    >
      <aside
        className="connectors-drawer"
        data-testid="caos-connectors-drawer"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="connectors-drawer-header">
          <div>
            <h2 className="connectors-drawer-title">Connectors</h2>
            <p className="connectors-drawer-subtitle">
              Give Aria the keys to your workspace. Connect once, ask anything.
            </p>
          </div>
          <button
            className="connectors-drawer-close"
            data-testid="caos-connectors-drawer-close"
            onClick={onClose}
            type="button"
            aria-label="Close connectors drawer"
          >
            <X size={16} />
          </button>
        </div>

        <div className="connectors-drawer-body">
          {loading && !states.length ? (
            <div style={{ padding: 24, color: "rgba(226,232,240,0.5)", fontSize: 13, textAlign: "center" }}>
              Loading connectors…
            </div>
          ) : null}

          <div className="connectors-section-label">Workspace</div>
          <GoogleCard state={byProvider("google")} onChanged={refresh} />

          <div className="connectors-section-label">Knowledge</div>
          <ObsidianCard state={byProvider("obsidian")} onChanged={refresh} />

          <div className="connectors-section-label">Code</div>
          <GitHubCard state={byProvider("github")} onChanged={refresh} />

          <div className="connectors-section-label">Communications</div>
          <SlackCard state={byProvider("slack")} onChanged={refresh} />
          <TwilioCard state={byProvider("twilio")} onChanged={refresh} />
          <TelegramCard state={byProvider("telegram")} onChanged={refresh} />

          <div className="connectors-section-label">Universal</div>
          <McpCard state={byProvider("mcp")} onChanged={refresh} />
        </div>
      </aside>
    </div>
  );
};

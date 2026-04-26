import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import axios from "axios";
import { toast } from "sonner";

import { useVoiceIO } from "@/components/caos/useVoiceIO";
import { useMemoryCrud } from "@/components/caos/useMemoryCrud";
import { useFilesCrud } from "@/components/caos/useFilesCrud";
import { API } from "@/config/apiBase";

const USER_KEY = "caos-shell-user-email";
const DEFAULT_RUNTIME = {
  key_source: "hybrid",
  default_provider: "openai",
  default_model: "gpt-5.2",
  enabled_providers: ["openai", "anthropic", "gemini", "xai"],
  provider_catalog: [],
};
const DEFAULT_VOICE = {
  stt_primary_model: "gpt-4o-transcribe",
  stt_fallback_model: "whisper-1",
  stt_language: "en",
  tts_model: "tts-1-hd",
  tts_voice: "nova",
  tts_speed: 1.0,
};

export const useCaosShell = (authenticatedUser = null) => {
  const [userEmail, setUserEmailState] = useState(() => authenticatedUser?.email || "michael@example.com");
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [profile, setProfile] = useState(null);
  const [artifacts, setArtifacts] = useState({ receipts: [], summaries: [], seeds: [] });
  const [continuity, setContinuity] = useState(null);
  const [files, setFiles] = useState([]);
  const [links, setLinks] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [lastTurn, setLastTurn] = useState(null);
  const [runtimeSettings, setRuntimeSettings] = useState(DEFAULT_RUNTIME);
  const [status, setStatus] = useState("Loading CAOS shell...");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [multiAgentMode, setMultiAgentModeState] = useState(() => localStorage.getItem("caos_multi_agent_mode") === "true");
  const voiceSettings = profile?.voice_preferences || DEFAULT_VOICE;

  // Memory Pulse — after every successful chat turn, the autonomous extractor
  // runs in the background. ~3.5s later we re-check the user's atom count;
  // if it grew, surface a tiny celebratory toast so the user feels Aria
  // learning. The toast's action opens the Memory Console drawer via a
  // custom DOM event (CaosShell listens for it).
  const prevAtomCountRef = useRef(null);
  // Per-session auto-backfill — once per session-load, fire-and-forget a
  // targeted mine of any unmined messages in this session. The backfill
  // service is idempotent (memory_extraction_log) so repeated calls are safe;
  // this ref just avoids hammering the endpoint within the same page load.
  const autoBackfillFiredRef = useRef({});
  const fireMemoryPulse = useCallback(async () => {
    if (!userEmail) return;
    try {
      const resp = await axios.get(`${API}/caos/memory/atoms`, {
        params: { user_email: userEmail },
      });
      const total = resp.data?.total || 0;
      const prev = prevAtomCountRef.current;
      prevAtomCountRef.current = total;
      if (prev != null && total > prev) {
        const delta = total - prev;
        toast.success(`Aria saved ${delta} new memor${delta === 1 ? "y" : "ies"}`, {
          description: "Click View to inspect what changed.",
          duration: 6000,
          action: {
            label: "View",
            onClick: () => {
              window.dispatchEvent(new CustomEvent("caos:open-memory-console"));
            },
          },
        });
      }
    } catch {
      /* non-fatal — pulse is a courtesy */
    }
  }, [userEmail]);

  const setMultiAgentMode = useCallback((value) => {
    localStorage.setItem("caos_multi_agent_mode", String(value));
    setMultiAgentModeState(value);
  }, []);

  const commitUserEmail = useCallback((value) => {
    const nextValue = value.trim();
    if (!nextValue || nextValue === userEmail) return;
    localStorage.setItem(USER_KEY, nextValue);
    setUserEmailState(nextValue);
  }, [userEmail]);

  const loadSessions = useCallback(async () => {
    const response = await axios.get(`${API}/caos/sessions`, { params: { user_email: userEmail } });
    setSessions(response.data);
    return response.data;
  }, [userEmail]);

  const loadMessages = useCallback(async (sessionId) => {
    const response = await axios.get(`${API}/caos/sessions/${sessionId}/messages`);
    setMessages(response.data);
    return response.data;
  }, []);

  const loadProfile = useCallback(async () => {
    try {
      const response = await axios.get(`${API}/caos/profile/${encodeURIComponent(userEmail)}`);
      setProfile(response.data);
      return response.data;
    } catch {
      setProfile(null);
      return null;
    }
  }, [userEmail]);

  const loadRuntimeSettings = useCallback(async () => {
    const response = await axios.get(`${API}/caos/runtime/settings/${encodeURIComponent(userEmail)}`);
    setRuntimeSettings(response.data);
    return response.data;
  }, [userEmail]);

  const loadFiles = useCallback(async () => {
    const response = await axios.get(`${API}/caos/files`, { params: { user_email: userEmail } });
    setFiles(response.data);
    return response.data;
  }, [userEmail]);

  const loadSessionLinks = useCallback(async (sessionId) => {
    if (!sessionId) {
      setLinks([]);
      return [];
    }
    const response = await axios.get(`${API}/caos/sessions/${sessionId}/links`);
    setLinks(response.data);
    return response.data;
  }, []);

  const loadArtifacts = useCallback(async (sessionId) => {
    if (!sessionId) {
      setArtifacts({ receipts: [], summaries: [], seeds: [] });
      return { receipts: [], summaries: [], seeds: [] };
    }
    const response = await axios.get(`${API}/caos/sessions/${sessionId}/artifacts`);
    setArtifacts(response.data);
    return response.data;
  }, []);

  const loadContinuity = useCallback(async (sessionId) => {
    if (!sessionId) {
      setContinuity(null);
      return null;
    }
    const response = await axios.get(`${API}/caos/sessions/${sessionId}/continuity`);
    setContinuity(response.data);
    return response.data;
  }, []);

  const selectSession = useCallback(async (session) => {
    setCurrentSession(session);
    setBusy(true);
    setError("");
    try {
      await loadMessages(session.session_id);
      await loadArtifacts(session.session_id);
      await loadContinuity(session.session_id);
      await loadSessionLinks(session.session_id);
      await loadFiles();
      setStatus(`Loaded session ${session.title}.`);
      // Auto-incremental memory backfill — fire-and-forget the once-per-page
      // session-scoped mining job so by the time the user opens Memory
      // Console, atoms from THIS session are already filed. Idempotent on
      // the server (memory_extraction_log skips already-mined messages).
      if (userEmail && !autoBackfillFiredRef.current[session.session_id]) {
        autoBackfillFiredRef.current[session.session_id] = true;
        axios.post(`${API}/caos/memory/atoms/backfill`,
          { user_email: userEmail, session_id: session.session_id },
        ).catch(() => { /* non-fatal courtesy mining */ });
      }
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Failed to load session.";
      setError(message);
      setStatus(`Failed to load session: ${message}`);
    } finally {
      setBusy(false);
    }
  }, [loadArtifacts, loadContinuity, loadFiles, loadMessages, loadSessionLinks, userEmail]);

  const createSession = useCallback(async (title = "New Thread") => {
    setBusy(true);
    setError("");
    try {
      await axios.post(`${API}/caos/profile/upsert`, {
        user_email: userEmail,
        preferred_name: "Michael",
      });
      await Promise.all([loadProfile(), loadRuntimeSettings(), loadFiles()]);
      const response = await axios.post(`${API}/caos/sessions`, {
        user_email: userEmail,
        title,
      });
      const nextSessions = await loadSessions();
      const created = nextSessions.find((item) => item.session_id === response.data.session_id) || response.data;
      setCurrentSession(created);
      setMessages([]);
      setArtifacts({ receipts: [], summaries: [], seeds: [] });
      setContinuity(null);
      setLinks([]);
      setLastTurn(null);
      setStatus(`Created session ${created.title}.`);
      return created;
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Failed to create session.";
      setError(message);
      setStatus(`Failed to create session: ${message}`);
      return null;
    } finally {
      setBusy(false);
    }
  }, [loadFiles, loadProfile, loadRuntimeSettings, loadSessions, userEmail]);

  const renameSession = useCallback(async (sessionId, nextTitle) => {
    if (!sessionId || !nextTitle?.trim()) return null;
    try {
      const response = await axios.patch(`${API}/caos/sessions/${sessionId}`, { title: nextTitle.trim() });
      await loadSessions();
      setCurrentSession((prev) => (prev?.session_id === sessionId ? { ...prev, ...response.data } : prev));
      setStatus(`Renamed thread to "${response.data.title}".`);
      return response.data;
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Rename failed.";
      setError(message);
      return null;
    }
  }, [loadSessions]);

  const toggleFlagSession = useCallback(async (session) => {
    if (!session?.session_id) return null;
    const next = !session.is_flagged;
    try {
      const response = await axios.patch(`${API}/caos/sessions/${session.session_id}`, { is_flagged: next });
      await loadSessions();
      setCurrentSession((prev) => (prev?.session_id === session.session_id ? { ...prev, ...response.data } : prev));
      setStatus(next ? "Flagged thread for follow-up." : "Unflagged thread.");
      return response.data;
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Flag failed.";
      setError(message);
      return null;
    }
  }, [loadSessions]);

  const deleteSession = useCallback(async (sessionId) => {
    if (!sessionId) return false;
    try {
      await axios.delete(`${API}/caos/sessions/${sessionId}`);
      const nextSessions = await loadSessions();
      setCurrentSession((prev) => {
        if (prev?.session_id !== sessionId) return prev;
        const fallback = nextSessions?.[0] || null;
        if (fallback) {
          loadMessages(fallback.session_id);
          loadArtifacts(fallback.session_id);
          loadContinuity(fallback.session_id);
          loadSessionLinks(fallback.session_id);
        } else {
          setMessages([]);
          setLinks([]);
        }
        return fallback;
      });
      setStatus("Thread deleted.");
      return true;
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Delete failed.";
      setError(message);
      return false;
    }
  }, [loadArtifacts, loadContinuity, loadMessages, loadSessionLinks, loadSessions]);

  const updateRuntimeSelection = useCallback(async (provider, model) => {
    setBusy(true);
    setError("");
    try {
      const response = await axios.post(`${API}/caos/runtime/settings`, {
        user_email: userEmail,
        key_source: runtimeSettings.key_source || "hybrid",
        default_provider: provider,
        default_model: model,
        enabled_providers: runtimeSettings.enabled_providers?.length ? runtimeSettings.enabled_providers : DEFAULT_RUNTIME.enabled_providers,
      });
      setRuntimeSettings(response.data);
      setStatus(`Aria is now routed through ${response.data.default_provider} · ${response.data.default_model}.`);
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Updating runtime failed.";
      setError(message);
      setStatus(`Updating runtime failed: ${message}`);
    } finally {
      setBusy(false);
    }
  }, [runtimeSettings.enabled_providers, runtimeSettings.key_source, userEmail]);

  const updateVoiceSettings = useCallback(async (changes) => {
    setBusy(true);
    setError("");
    try {
      const payload = { user_email: userEmail, ...voiceSettings, ...changes };
      const response = await axios.post(`${API}/caos/voice/settings`, payload);
      setProfile((previous) => ({
        ...(previous || { user_email: userEmail, structured_memory: [] }),
        voice_preferences: response.data.voice_preferences,
      }));
      setStatus(`Voice settings updated: ${response.data.voice_preferences.stt_primary_model} → ${response.data.voice_preferences.tts_voice}.`);
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Updating voice settings failed.";
      setError(message);
      setStatus(`Updating voice settings failed: ${message}`);
    } finally {
      setBusy(false);
    }
  }, [userEmail, voiceSettings]);

  const { saveMemory, updateMemory, deleteMemory } = useMemoryCrud({
    userEmail, loadProfile, setBusy, setError, setStatus,
  });

  const { uploadFile, saveLink } = useFilesCrud({
    userEmail, currentSession, loadFiles, loadSessionLinks, setBusy, setError, setStatus,
  });

  const { transcribeAudio, transcribeAudioChunk, speakText } = useVoiceIO({
    userEmail, voiceSettings,
  });

  const sendMessage = useCallback(async (content) => {
    if (!content.trim()) return;
    setBusy(true);
    setError("");
    const trimmed = content.trim();
    const now = new Date().toISOString();
    const pendingUserId = `pending-user-${Date.now()}`;
    const pendingAssistantId = `pending-assistant-${Date.now() + 1}`;
    let session = currentSession;
    let effectiveProvider = runtimeSettings.default_provider;
    let effectiveModel = runtimeSettings.default_model;
    setMessages((prev) => [
      ...prev,
      { id: pendingUserId, role: "user", content: trimmed, timestamp: now, pending: true },
      { id: pendingAssistantId, role: "assistant", content: "", timestamp: now, pending: true, streaming: true },
    ]);
    try {
      if (!session) session = await createSession(trimmed.slice(0, 48) || "New Thread");
      if (!session) {
        setMessages((prev) => prev.filter((m) => m.id !== pendingUserId && m.id !== pendingAssistantId));
        return;
      }

      // Respect the user's engine choice. We DO NOT silently override to Gemini
      // when the session has attachments — that previously hijacked the toggle
      // (Claude → Gemini behind the user's back). If the user wants Gemini's
      // image vision, they can switch manually. We surface a hint instead.
      const sessionImages = files.filter((f) => f.session_id === session.session_id && (f.mime_type || "").startsWith("image/"));
      if (sessionImages.length > 0 && effectiveProvider !== "gemini") {
        setStatus(`Heads up: only Gemini can see image contents. ${effectiveProvider} sees just filenames in this turn.`);
      }

      // Multi-agent branch: fan out to Claude/OpenAI/Gemini + Synthesizer. Replace
      // the pending assistant bubble with a multi-agent group once all return.
      if (multiAgentMode) {
        try {
          const multiResponse = await axios.post(`${API}/caos/chat/multi`, {
            user_email: userEmail,
            session_id: session.session_id,
            content: trimmed,
            provider: effectiveProvider,
            model: effectiveModel,
          });
          setMessages((prev) => prev.map((message) => message.id === pendingAssistantId
            ? {
                id: pendingAssistantId,
                role: "assistant",
                timestamp: now,
                pending: false,
                multi_agent: true,
                agents: multiResponse.data.agents,
                synthesis: multiResponse.data.synthesis,
                content: "",
              }
            : message));
          const nextSessions = await loadSessions();
          setCurrentSession(nextSessions.find((item) => item.session_id === session.session_id) || session);
          await loadArtifacts(session.session_id);
          await loadProfile();
          const synthOk = multiResponse.data.synthesis?.ok ? " · synthesized" : "";
          setStatus(`Multi-agent · ${multiResponse.data.ok_count}/${multiResponse.data.agents.length} succeeded${synthOk}`);
          setTimeout(() => { fireMemoryPulse(); }, 3500);
          return;
        } catch (multiError) {
          setMessages((prev) => prev.filter((m) => m.id !== pendingAssistantId));
          throw multiError;
        }
      }

      // Single-agent branch: SSE streaming — progressively paint words. Falls back to POST /chat on failure.
      let finalPayload = null;
      const streamResponse = await fetch(`${API}/caos/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_email: userEmail,
          session_id: session.session_id,
          content: trimmed,
          provider: effectiveProvider,
          model: effectiveModel,
        }),
      });

      if (streamResponse.ok && streamResponse.body) {
        const reader = streamResponse.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let accumulated = "";
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const parts = buffer.split("\n\n");
          buffer = parts.pop() || "";
          for (const part of parts) {
            const eventLine = part.split("\n").find((line) => line.startsWith("event:"));
            const dataLine = part.split("\n").find((line) => line.startsWith("data:"));
            if (!eventLine || !dataLine) continue;
            const eventType = eventLine.slice(6).trim();
            const dataRaw = dataLine.slice(5).trim();
            let data;
            try { data = JSON.parse(dataRaw); } catch { continue; }
            if (eventType === "delta") {
              accumulated = data.cumulative || `${accumulated}${data.delta || ""}`;
              setMessages((prev) => prev.map((m) => m.id === pendingAssistantId
                ? { ...m, content: accumulated, streaming: true }
                : m));
            } else if (eventType === "final") {
              finalPayload = data;
            } else if (eventType === "error") {
              throw new Error(data.error || "stream_failed");
            }
          }
        }
      } else {
        throw new Error(`stream_unavailable_${streamResponse.status}`);
      }

      if (finalPayload) setLastTurn(finalPayload);
      const nextSessions = await loadSessions();
      setCurrentSession(nextSessions.find((item) => item.session_id === session.session_id) || session);
      await loadMessages(session.session_id);
      await loadArtifacts(session.session_id);
      await loadContinuity(session.session_id);
      await loadSessionLinks(session.session_id);
      await loadProfile();
      await loadFiles();
      // Memory Pulse — extractor runs ~1–3s after chat. Wait ~3.5s then diff.
      setTimeout(() => { fireMemoryPulse(); }, 3500);
      setStatus("CAOS replied with session-scoped context.");
    } catch (issue) {
      const rawMessage = issue?.response?.data?.detail || issue?.message || "Sending message failed.";
      // Sanitize: never render raw Pydantic / Python tracebacks in the chat bubble.
      // Backend already maps known error codes to friendly text, but defense in depth.
      let message;
      if (rawMessage.startsWith("stream_unavailable_")) {
        message = "This engine did not answer in time. Your draft is preserved below so you can retry or switch engines.";
      } else if (/validation error|field required|pydantic/i.test(rawMessage)) {
        message = "Engine returned an unexpected response. Try again or switch engines.";
      } else if (rawMessage.length > 200) {
        message = `${rawMessage.slice(0, 180)}…`;
      } else {
        message = rawMessage;
      }
      setError(message);
      // OPEN-03 fix: clear the stale receipt so the WCW meter doesn't freeze
      // on the previous turn's token count when the engine fails. The meter
      // gracefully falls back to the dynamic budget default until next reply.
      setLastTurn(null);
      let syncedMessages = null;
      if (session?.session_id) {
        try {
          syncedMessages = await loadMessages(session.session_id);
          await loadArtifacts(session.session_id);
          await loadContinuity(session.session_id);
          await loadSessionLinks(session.session_id);
          await loadFiles();
        } catch {
          syncedMessages = null;
        }
      }
      const providerLabel = `${effectiveProvider || runtimeSettings.default_provider} · ${effectiveModel || runtimeSettings.default_model}`;
      setStatus(`Reply failed on ${providerLabel}: ${message}`);
      setMessages((prev) => {
        const failedDraft = {
          id: pendingUserId,
          role: "user",
          content: trimmed,
          timestamp: now,
          pending: false,
          failed: true,
          error: message,
        };
        const alreadyPersisted = syncedMessages?.some((entry) => entry.role === "user" && entry.content?.trim() === trimmed) || false;
        const failureNotice = {
          id: `system-failure-${Date.now()}`,
          role: "system",
          content: alreadyPersisted
            ? `Your message was received, but ${providerLabel} failed before Aria could reply.`
            : `The request failed before ${providerLabel} could reply. Your draft is preserved below so you can retry or switch engines.`,
          error: message,
          failed: true,
          timestamp: new Date().toISOString(),
        };
        if (syncedMessages?.length) {
          return alreadyPersisted ? [...syncedMessages, failureNotice] : [...syncedMessages, failedDraft, failureNotice];
        }
        return [
          ...prev
            .filter((m) => m.id !== pendingAssistantId)
            .map((m) => (m.id === pendingUserId ? failedDraft : m)),
          failureNotice,
        ];
      });
    } finally {
      setBusy(false);
    }
  }, [createSession, currentSession, files, fireMemoryPulse, loadArtifacts, loadContinuity, loadFiles, loadMessages, loadProfile, loadSessionLinks, loadSessions, multiAgentMode, runtimeSettings.default_model, runtimeSettings.default_provider, userEmail]);

  useEffect(() => {
    const hydrate = async () => {
      setBusy(true);
      try {
        const foundSessions = await loadSessions();
        await Promise.all([loadProfile(), loadRuntimeSettings(), loadFiles()]);
        // Seed the memory-pulse baseline so the FIRST chat turn doesn't
        // toast against a null prev count and miss the diff.
        try {
          const memResp = await axios.get(`${API}/caos/memory/atoms`, {
            params: { user_email: userEmail },
          });
          prevAtomCountRef.current = memResp.data?.total || 0;
        } catch { /* non-fatal */ }
        if (foundSessions.length) {
          // Prefer the most-recent NON-EMPTY session. The user complaint:
          // "login routes to empty thread instead of resuming last conversation".
          // Root cause was that "New Thread" creates a session with updated_at=now
          // but zero messages — that empty stub became position [0] and we
          // auto-loaded it. Now we walk the list (already sorted by updated_at
          // desc on the backend) and pick the first one with a populated
          // `last_message_preview`. Fall back to [0] only if every session is
          // empty (truly first-time user state).
          const populated = foundSessions.find((session) => {
            const preview = (session.last_message_preview || "").trim();
            return preview.length > 0;
          });
          const target = populated || foundSessions[0];
          setCurrentSession(target);
          await loadMessages(target.session_id);
          await loadArtifacts(target.session_id);
          await loadContinuity(target.session_id);
          await loadSessionLinks(target.session_id);
          if (populated) {
            setStatus(`Resumed your last conversation: ${target.title}.`);
          } else {
            setStatus(`Loaded ${foundSessions.length} saved sessions.`);
          }
        } else {
          setMessages([]);
          setLinks([]);
          setStatus("No sessions yet. Start a thread to begin the CAOS shell.");
        }
      } catch (issue) {
        const message = issue?.response?.data?.detail || issue?.message || "Shell bootstrap failed.";
        setError(message);
        setStatus(`Shell bootstrap failed: ${message}`);
      } finally {
        setBusy(false);
      }
    };
    hydrate();
  }, [loadArtifacts, loadContinuity, loadFiles, loadMessages, loadProfile, loadRuntimeSettings, loadSessionLinks, loadSessions]);

  const filteredMessages = useMemo(() => {
    if (!searchQuery.trim()) return messages;
    const lowered = searchQuery.toLowerCase();
    return messages.filter((message) => message.content?.toLowerCase().includes(lowered));
  }, [messages, searchQuery]);

  const updateProfile = useCallback(async (changes) => {
    if (!userEmail) return null;
    const response = await axios.post(`${API}/caos/profile/upsert`, {
      user_email: userEmail, ...changes,
    });
    await loadProfile();
    return response.data;
  }, [loadProfile, userEmail]);

  return {
    artifacts, busy, continuity, createSession, currentSession, deleteSession, error, filteredMessages,
    files, lastTurn, links, messages, multiAgentMode, profile, renameSession, runtimeSettings, searchQuery,
    selectSession, sendMessage, sessions, setMultiAgentMode, setSearchQuery, commitUserEmail,
    saveLink, saveMemory, speakText, status, toggleFlagSession, transcribeAudio, transcribeAudioChunk,
    updateMemory, updateProfile, updateRuntimeSelection, updateVoiceSettings, uploadFile,
    userEmail, deleteMemory, voiceSettings,
  };
};

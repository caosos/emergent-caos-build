import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";

import { useVoiceIO } from "@/components/caos/useVoiceIO";
import { useMemoryCrud } from "@/components/caos/useMemoryCrud";
import { useFilesCrud } from "@/components/caos/useFilesCrud";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
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
  const [searchQuery, setSearchQuery] = useState("");
  const [lastTurn, setLastTurn] = useState(null);
  const [runtimeSettings, setRuntimeSettings] = useState(DEFAULT_RUNTIME);
  const [status, setStatus] = useState("Loading CAOS shell...");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [multiAgentMode, setMultiAgentModeState] = useState(() => localStorage.getItem("caos_multi_agent_mode") === "true");
  const voiceSettings = profile?.voice_preferences || DEFAULT_VOICE;

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
      await loadFiles();
      setStatus(`Loaded session ${session.title}.`);
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Failed to load session.";
      setError(message);
      setStatus(`Failed to load session: ${message}`);
    } finally {
      setBusy(false);
    }
  }, [loadArtifacts, loadContinuity, loadFiles, loadMessages]);

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
    userEmail, currentSession, loadFiles, setBusy, setError, setStatus,
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
    setMessages((prev) => [
      ...prev,
      { id: pendingUserId, role: "user", content: trimmed, timestamp: now, pending: true },
      { id: pendingAssistantId, role: "assistant", content: "", timestamp: now, pending: true, streaming: true },
    ]);
    try {
      let session = currentSession;
      if (!session) session = await createSession(trimmed.slice(0, 48) || "New Thread");
      if (!session) {
        setMessages((prev) => prev.filter((m) => m.id !== pendingUserId && m.id !== pendingAssistantId));
        return;
      }

      // Auto-route to Gemini when images are attached on Claude/GPT (Gemini is the
      // only provider whose binary attachments are supported by emergentintegrations).
      const sessionImages = files.filter((f) => f.session_id === session.session_id && (f.mime_type || "").startsWith("image/"));
      let effectiveProvider = runtimeSettings.default_provider;
      let effectiveModel = runtimeSettings.default_model;
      if (sessionImages.length > 0 && effectiveProvider !== "gemini") {
        effectiveProvider = "gemini";
        effectiveModel = "gemini-3-flash-preview";
        setStatus(`Auto-routed to Gemini so it can see your ${sessionImages.length} image${sessionImages.length === 1 ? "" : "s"}.`);
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
      await loadProfile();
      await loadFiles();
      setStatus("CAOS replied with session-scoped context.");
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Sending message failed.";
      setError(message);
      setStatus(`Sending message failed: ${message}`);
      setMessages((prev) => prev.filter((m) => m.id !== pendingAssistantId));
    } finally {
      setBusy(false);
    }
  }, [createSession, currentSession, files, loadArtifacts, loadContinuity, loadFiles, loadMessages, loadProfile, loadSessions, multiAgentMode, runtimeSettings.default_model, runtimeSettings.default_provider, userEmail]);

  useEffect(() => {
    const hydrate = async () => {
      setBusy(true);
      try {
        const foundSessions = await loadSessions();
        await Promise.all([loadProfile(), loadRuntimeSettings(), loadFiles()]);
        if (foundSessions[0]) {
          setCurrentSession(foundSessions[0]);
          await loadMessages(foundSessions[0].session_id);
          await loadArtifacts(foundSessions[0].session_id);
          await loadContinuity(foundSessions[0].session_id);
          setStatus(`Loaded ${foundSessions.length} saved sessions.`);
        } else {
          setMessages([]);
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
  }, [loadArtifacts, loadContinuity, loadFiles, loadMessages, loadProfile, loadRuntimeSettings, loadSessions]);

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
    artifacts, busy, continuity, createSession, currentSession, error, filteredMessages,
    files, lastTurn, messages, multiAgentMode, profile, runtimeSettings, searchQuery,
    selectSession, sendMessage, sessions, setMultiAgentMode, setSearchQuery, commitUserEmail,
    saveLink, saveMemory, speakText, status, transcribeAudio, transcribeAudioChunk,
    updateMemory, updateProfile, updateRuntimeSelection, updateVoiceSettings, uploadFile,
    userEmail, deleteMemory, voiceSettings,
  };
};

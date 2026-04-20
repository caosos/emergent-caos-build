import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";


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


export const useCaosShell = () => {
  const [userEmail, setUserEmailState] = useState(() => localStorage.getItem(USER_KEY) || "michael@example.com");
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
  const voiceSettings = profile?.voice_preferences || DEFAULT_VOICE;

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
      const payload = {
        user_email: userEmail,
        ...voiceSettings,
        ...changes,
      };
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

  const saveMemory = useCallback(async (content, binName = "general") => {
    if (!content.trim()) return;
    setBusy(true);
    setError("");
    try {
      await axios.post(`${API}/caos/memory/save`, {
        user_email: userEmail,
        content,
        bin_name: binName,
      });
      await loadProfile();
      setStatus(`Saved ${binName === "personal_facts" ? "personal fact" : "memory"}.`);
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Saving memory failed.";
      setError(message);
      setStatus(`Saving memory failed: ${message}`);
    } finally {
      setBusy(false);
    }
  }, [loadProfile, userEmail]);

  const updateMemory = useCallback(async (memoryId, changes) => {
    setBusy(true);
    setError("");
    try {
      await axios.patch(`${API}/caos/memory/${memoryId}`, {
        user_email: userEmail,
        ...changes,
      });
      await loadProfile();
      setStatus("Memory updated.");
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Updating memory failed.";
      setError(message);
      setStatus(`Updating memory failed: ${message}`);
    } finally {
      setBusy(false);
    }
  }, [loadProfile, userEmail]);

  const deleteMemory = useCallback(async (memoryId) => {
    setBusy(true);
    setError("");
    try {
      await axios.delete(`${API}/caos/memory/${memoryId}`, { params: { user_email: userEmail } });
      await loadProfile();
      setStatus("Memory deleted.");
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Deleting memory failed.";
      setError(message);
      setStatus(`Deleting memory failed: ${message}`);
    } finally {
      setBusy(false);
    }
  }, [loadProfile, userEmail]);

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
      if (!session) {
        session = await createSession(trimmed.slice(0, 48) || "New Thread");
      }
      if (!session) {
        setMessages((prev) => prev.filter((message) => message.id !== pendingUserId && message.id !== pendingAssistantId));
        return;
      }

      // Try SSE streaming first — progressively paint words into the placeholder.
      // Any failure cleanly falls back to the POST /chat path.
      let finalPayload = null;
      const streamResponse = await fetch(`${API}/caos/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_email: userEmail,
          session_id: session.session_id,
          content: trimmed,
          provider: runtimeSettings.default_provider,
          model: runtimeSettings.default_model,
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
              setMessages((prev) => prev.map((message) => message.id === pendingAssistantId
                ? { ...message, content: accumulated, streaming: true }
                : message));
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
      const refreshedSession = nextSessions.find((item) => item.session_id === session.session_id) || session;
      setCurrentSession(refreshedSession);
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
  }, [createSession, currentSession, loadArtifacts, loadContinuity, loadFiles, loadMessages, loadProfile, loadSessions, runtimeSettings.default_model, runtimeSettings.default_provider, userEmail]);

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

  const uploadFile = useCallback(async (file) => {
    if (!file) return;
    const form = new FormData();
    form.append("user_email", userEmail);
    if (currentSession?.session_id) form.append("session_id", currentSession.session_id);
    form.append("file", file);
    setBusy(true);
    setError("");
    try {
      await axios.post(`${API}/caos/files/upload`, form);
      await loadFiles();
      setStatus(`Uploaded ${file.name}.`);
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Upload failed.";
      setError(message);
      setStatus(`Upload failed: ${message}`);
    } finally {
      setBusy(false);
    }
  }, [currentSession, loadFiles, userEmail]);

  const saveLink = useCallback(async (url, label) => {
    if (!url.trim() || !label.trim()) return;
    setBusy(true);
    setError("");
    try {
      await axios.post(`${API}/caos/files/link`, {
        user_email: userEmail,
        session_id: currentSession?.session_id || null,
        url,
        label,
      });
      await loadFiles();
      setStatus(`Saved link ${label}.`);
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Saving link failed.";
      setError(message);
      setStatus(`Saving link failed: ${message}`);
    } finally {
      setBusy(false);
    }
  }, [currentSession, loadFiles, userEmail]);

  const transcribeAudio = useCallback(async (blob, filename = "caos-voice-note.webm") => {
    const form = new FormData();
    form.append("user_email", userEmail);
    form.append("model", voiceSettings.stt_primary_model);
    form.append("fallback_model", voiceSettings.stt_fallback_model);
    form.append("language", voiceSettings.stt_language);
    form.append("file", new File([blob], filename, { type: blob.type || "audio/webm" }));
    const response = await axios.post(`${API}/caos/voice/transcribe`, form);
    return response.data;
  }, [userEmail, voiceSettings.stt_fallback_model, voiceSettings.stt_language, voiceSettings.stt_primary_model]);

  const transcribeAudioChunk = useCallback(async (blob, prompt = "", filename = "caos-voice-chunk.webm") => {
    const form = new FormData();
    form.append("user_email", userEmail);
    form.append("model", voiceSettings.stt_primary_model);
    form.append("fallback_model", voiceSettings.stt_fallback_model);
    form.append("language", voiceSettings.stt_language);
    if (prompt.trim()) form.append("prompt", prompt.slice(-180));
    form.append("file", new File([blob], filename, { type: blob.type || "audio/webm" }));
    const response = await axios.post(`${API}/caos/voice/transcribe`, form);
    return response.data;
  }, [userEmail, voiceSettings.stt_fallback_model, voiceSettings.stt_language, voiceSettings.stt_primary_model]);

  const speakText = useCallback(async (text, overrides = {}) => {
    // Primary path: OpenAI TTS via backend (Base44 Path A parity).
    // Fallback path: browser speechSynthesis (Base44 Path B parity).
    // Any backend failure silently falls through so Read Aloud never blocks the user.
    try {
      const response = await axios.post(`${API}/caos/voice/tts`, {
        text,
        voice: overrides.voice || voiceSettings.tts_voice,
        model: overrides.model || voiceSettings.tts_model,
        speed: overrides.speed || voiceSettings.tts_speed,
      });
      const audio = new Audio(`data:${response.data.content_type};base64,${response.data.audio_base64}`);
      await audio.play();
      return audio;
    } catch (error) {
      if (typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.cancel();
        const utter = new SpeechSynthesisUtterance(text);
        utter.rate = overrides.speed || voiceSettings.tts_speed || 1.0;
        window.speechSynthesis.speak(utter);
        return utter;
      }
      throw error;
    }
  }, [voiceSettings.tts_model, voiceSettings.tts_speed, voiceSettings.tts_voice]);

  const updateProfile = useCallback(async (changes) => {
    if (!userEmail) return null;
    const response = await axios.post(`${API}/caos/profile/upsert`, {
      user_email: userEmail,
      ...changes,
    });
    await loadProfile();
    return response.data;
  }, [loadProfile, userEmail]);

  return {
    artifacts,
    busy,
    continuity,
    createSession,
    currentSession,
    error,
    filteredMessages,
    files,
    lastTurn,
    messages,
    profile,
    runtimeSettings,
    searchQuery,
    selectSession,
    sendMessage,
    sessions,
    setSearchQuery,
    commitUserEmail,
    saveLink,
    saveMemory,
    speakText,
    status,
    transcribeAudio,
    transcribeAudioChunk,
    updateMemory,
    updateProfile,
    updateRuntimeSelection,
    updateVoiceSettings,
    uploadFile,
    userEmail,
    deleteMemory,
    voiceSettings,
  };
};
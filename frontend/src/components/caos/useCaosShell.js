import { useCallback, useEffect, useMemo, useState } from "react";
import axios from "axios";


const API = `${process.env.REACT_APP_BACKEND_URL}/api`;
const USER_KEY = "caos-shell-user-email";


export const useCaosShell = () => {
  const [userEmail, setUserEmailState] = useState(() => localStorage.getItem(USER_KEY) || "michael@example.com");
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [profile, setProfile] = useState(null);
  const [artifacts, setArtifacts] = useState({ receipts: [], summaries: [], seeds: [] });
  const [files, setFiles] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [lastTurn, setLastTurn] = useState(null);
  const [status, setStatus] = useState("Loading CAOS shell...");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

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

  const selectSession = useCallback(async (session) => {
    setCurrentSession(session);
    setBusy(true);
    setError("");
    try {
      await loadMessages(session.session_id);
      await loadArtifacts(session.session_id);
      await loadFiles();
      setStatus(`Loaded session ${session.title}.`);
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Failed to load session.";
      setError(message);
      setStatus(`Failed to load session: ${message}`);
    } finally {
      setBusy(false);
    }
  }, [loadArtifacts, loadFiles, loadMessages]);

  const createSession = useCallback(async (title = "New Thread") => {
    setBusy(true);
    setError("");
    try {
      await axios.post(`${API}/caos/profile/upsert`, {
        user_email: userEmail,
        preferred_name: "Michael",
      });
      await loadProfile();
      await loadFiles();
      const response = await axios.post(`${API}/caos/sessions`, {
        user_email: userEmail,
        title,
      });
      const nextSessions = await loadSessions();
      const created = nextSessions.find((item) => item.session_id === response.data.session_id) || response.data;
      setCurrentSession(created);
      setMessages([]);
      setArtifacts({ receipts: [], summaries: [], seeds: [] });
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
  }, [loadFiles, loadProfile, loadSessions, userEmail]);

  const sendMessage = useCallback(async (content) => {
    if (!content.trim()) return;
    setBusy(true);
    setError("");
    try {
      let session = currentSession;
      if (!session) {
        session = await createSession(content.slice(0, 48) || "New Thread");
      }
      if (!session) return;
      const response = await axios.post(`${API}/caos/chat`, {
        user_email: userEmail,
        session_id: session.session_id,
        content,
      });
      setLastTurn(response.data);
      const nextSessions = await loadSessions();
      const refreshedSession = nextSessions.find((item) => item.session_id === session.session_id) || session;
      setCurrentSession(refreshedSession);
      await loadMessages(session.session_id);
      await loadArtifacts(session.session_id);
      await loadProfile();
      await loadFiles();
      setStatus("CAOS replied with session-scoped context.");
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Sending message failed.";
      setError(message);
      setStatus(`Sending message failed: ${message}`);
    } finally {
      setBusy(false);
    }
  }, [createSession, currentSession, loadArtifacts, loadFiles, loadMessages, loadProfile, loadSessions, userEmail]);

  useEffect(() => {
    const hydrate = async () => {
      setBusy(true);
      try {
        const foundSessions = await loadSessions();
        await loadProfile();
        await loadFiles();
        if (foundSessions[0]) {
          setCurrentSession(foundSessions[0]);
          await loadMessages(foundSessions[0].session_id);
          await loadArtifacts(foundSessions[0].session_id);
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
  }, [loadArtifacts, loadFiles, loadMessages, loadProfile, loadSessions]);

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
    form.append("file", new File([blob], filename, { type: blob.type || "audio/webm" }));
    const response = await axios.post(`${API}/caos/voice/transcribe`, form);
    return response.data.text || "";
  }, []);

  const speakText = useCallback(async (text) => {
    const response = await axios.post(`${API}/caos/voice/tts`, { text, voice: "nova", model: "tts-1-hd", speed: 1.0 });
    const audio = new Audio(`data:${response.data.content_type};base64,${response.data.audio_base64}`);
    await audio.play();
    return audio;
  }, []);

  return {
    artifacts,
    busy,
    createSession,
    currentSession,
    error,
    filteredMessages,
    files,
    lastTurn,
    messages,
    profile,
    searchQuery,
    selectSession,
    sendMessage,
    sessions,
    setSearchQuery,
    commitUserEmail,
    saveLink,
    speakText,
    status,
    transcribeAudio,
    uploadFile,
    userEmail,
  };
};
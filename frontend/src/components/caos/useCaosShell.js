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
  const [searchQuery, setSearchQuery] = useState("");
  const [lastTurn, setLastTurn] = useState(null);
  const [status, setStatus] = useState("Loading CAOS shell...");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const setUserEmail = useCallback((value) => {
    localStorage.setItem(USER_KEY, value);
    setUserEmailState(value);
  }, []);

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
      setStatus(`Loaded session ${session.title}.`);
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Failed to load session.";
      setError(message);
      setStatus(`Failed to load session: ${message}`);
    } finally {
      setBusy(false);
    }
  }, [loadMessages]);

  const createSession = useCallback(async (title = "New Thread") => {
    setBusy(true);
    setError("");
    try {
      await axios.post(`${API}/caos/profile/upsert`, {
        user_email: userEmail,
        preferred_name: "Michael",
      });
      await loadProfile();
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
  }, [loadSessions, userEmail]);

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
      setStatus("CAOS replied with session-scoped context.");
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Sending message failed.";
      setError(message);
      setStatus(`Sending message failed: ${message}`);
    } finally {
      setBusy(false);
    }
  }, [createSession, currentSession, loadMessages, loadSessions, userEmail]);

  useEffect(() => {
    const hydrate = async () => {
      setBusy(true);
      try {
        const foundSessions = await loadSessions();
        await loadProfile();
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
  }, [loadMessages, loadSessions]);

  const filteredMessages = useMemo(() => {
    if (!searchQuery.trim()) return messages;
    const lowered = searchQuery.toLowerCase();
    return messages.filter((message) => message.content?.toLowerCase().includes(lowered));
  }, [messages, searchQuery]);

  return {
    artifacts,
    busy,
    createSession,
    currentSession,
    error,
    filteredMessages,
    lastTurn,
    messages,
    profile,
    searchQuery,
    selectSession,
    sendMessage,
    sessions,
    setSearchQuery,
    setUserEmail,
    status,
    userEmail,
  };
};
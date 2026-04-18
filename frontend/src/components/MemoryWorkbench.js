import { useEffect, useMemo, useState } from "react";
import axios from "axios";


const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;


const emptyReceipt = {
  retrieval_terms: [],
  selected_memory_ids: [],
  injected_memory_count: 0,
  final_message_count: 0,
  estimated_chars_before: 0,
  estimated_chars_after: 0,
  reduction_ratio: 0,
};


export const MemoryWorkbench = () => {
  const [contract, setContract] = useState(null);
  const [userEmail, setUserEmail] = useState("michael@example.com");
  const [sessionTitle, setSessionTitle] = useState("CAOS memory isolation lab");
  const [sessionId, setSessionId] = useState("");
  const [memoryText, setMemoryText] = useState("Utility bill due Friday. Campaign Atlas is active.");
  const [messageText, setMessageText] = useState("I just got off work. What matters right now?");
  const [query, setQuery] = useState("What matters right now about Atlas and the bill?");
  const [memories, setMemories] = useState([]);
  const [messages, setMessages] = useState([]);
  const [contextResult, setContextResult] = useState(null);
  const [status, setStatus] = useState("Booting CAOS memory workbench...");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const loadContract = async () => {
      const response = await axios.get(`${API}/caos/contract`);
      setContract(response.data);
      setStatus("Contract loaded. Session isolation is active.");
    };
    loadContract().catch(() => setStatus("Backend contract unavailable."));
  }, []);

  const stats = contextResult?.stats || emptyReceipt;
  const receipt = contextResult?.receipt || emptyReceipt;
  const reductionPercent = useMemo(
    () => `${Math.round((stats.reduction_ratio || 0) * 100)}%`,
    [stats.reduction_ratio]
  );

  const ensureProfile = async () => {
    await axios.post(`${API}/caos/profile/upsert`, {
      user_email: userEmail,
      preferred_name: "Michael",
    });
  };

  const handleCreateSession = async () => {
    setBusy(true);
    try {
      await ensureProfile();
      const response = await axios.post(`${API}/caos/sessions`, {
        user_email: userEmail,
        title: sessionTitle,
      });
      setSessionId(response.data.session_id);
      setMessages([]);
      setContextResult(null);
      setStatus(`Session ${response.data.session_id} created.`);
    } finally {
      setBusy(false);
    }
  };

  const handleSaveMemory = async () => {
    setBusy(true);
    try {
      await ensureProfile();
      const response = await axios.post(`${API}/caos/memory/save`, {
        user_email: userEmail,
        content: memoryText,
      });
      setMemories((prev) => [response.data, ...prev]);
      setStatus("Memory saved to structured profile memory.");
    } finally {
      setBusy(false);
    }
  };

  const handleAddMessage = async () => {
    if (!sessionId) {
      setStatus("Create a session before writing messages.");
      return;
    }
    setBusy(true);
    try {
      const response = await axios.post(`${API}/caos/messages`, {
        session_id: sessionId,
        role: "user",
        content: messageText,
      });
      setMessages((prev) => [...prev, response.data]);
      setStatus("Message stored inside the current isolated session.");
    } finally {
      setBusy(false);
    }
  };

  const handlePrepareContext = async () => {
    if (!sessionId) {
      setStatus("Create a session before preparing context.");
      return;
    }
    setBusy(true);
    try {
      const response = await axios.post(`${API}/caos/context/prepare`, {
        user_email: userEmail,
        session_id: sessionId,
        query,
      });
      setContextResult(response.data);
      setStatus("Context prepared. Sanitized history and relevant memories are ready.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="workbench-shell" data-testid="memory-workbench-shell">
      <section className="hero-panel" data-testid="memory-workbench-hero-panel">
        <div className="hero-copy">
          <p className="eyebrow" data-testid="memory-workbench-eyebrow">CAOS Replatform</p>
          <h1 className="hero-title" data-testid="memory-workbench-title">
            Session isolation and memory sanitization come first.
          </h1>
          <p className="hero-subtitle" data-testid="memory-workbench-subtitle">
            This workbench proves the first Python contract: isolate by session, cleanse context, retrieve only what matters, and show the receipt.
          </p>
        </div>
        <div className="contract-card" data-testid="memory-workbench-contract-card">
          <div className="contract-row" data-testid="memory-contract-runtime">
            <span>Runtime</span>
            <strong>{contract?.runtime || "loading"}</strong>
          </div>
          <div className="contract-row" data-testid="memory-contract-boundary">
            <span>Isolation</span>
            <strong>{contract?.isolation_boundary || "loading"}</strong>
          </div>
          <div className="contract-row" data-testid="memory-contract-pipeline">
            <span>Pipeline</span>
            <strong>{contract?.memory_pipeline?.join(" → ") || "loading"}</strong>
          </div>
        </div>
      </section>

      <section className="grid-zone" data-testid="memory-workbench-grid">
        <article className="panel" data-testid="session-setup-panel">
          <h2 data-testid="session-setup-heading">Session setup</h2>
          <label htmlFor="user-email" data-testid="session-user-email-label">User email</label>
          <input
            id="user-email"
            data-testid="session-user-email-input"
            value={userEmail}
            onChange={(event) => setUserEmail(event.target.value)}
          />
          <label htmlFor="session-title" data-testid="session-title-label">Session title</label>
          <input
            id="session-title"
            data-testid="session-title-input"
            value={sessionTitle}
            onChange={(event) => setSessionTitle(event.target.value)}
          />
          <button
            className="primary-button"
            data-testid="create-session-button"
            disabled={busy}
            onClick={handleCreateSession}
          >
            Create isolated session
          </button>
          <div className="pill" data-testid="active-session-id-display">
            Active session: {sessionId || "none yet"}
          </div>
        </article>

        <article className="panel" data-testid="memory-save-panel">
          <h2 data-testid="memory-save-heading">Structured memory</h2>
          <label htmlFor="memory-text" data-testid="memory-text-label">Memory entry</label>
          <textarea
            id="memory-text"
            data-testid="memory-textarea"
            rows={5}
            value={memoryText}
            onChange={(event) => setMemoryText(event.target.value)}
          />
          <button
            className="secondary-button"
            data-testid="save-memory-button"
            disabled={busy}
            onClick={handleSaveMemory}
          >
            Save structured memory
          </button>
          <div className="list-stack" data-testid="saved-memories-list">
            {memories.map((memory) => (
              <div className="list-card" key={memory.id} data-testid={`saved-memory-${memory.id}`}>
                <strong>{memory.content}</strong>
                <span>{memory.tags.join(", ")}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel" data-testid="session-messages-panel">
          <h2 data-testid="session-messages-heading">Session messages</h2>
          <label htmlFor="message-text" data-testid="message-text-label">User message</label>
          <textarea
            id="message-text"
            data-testid="message-textarea"
            rows={5}
            value={messageText}
            onChange={(event) => setMessageText(event.target.value)}
          />
          <button
            className="secondary-button"
            data-testid="add-message-button"
            disabled={busy}
            onClick={handleAddMessage}
          >
            Add message to session
          </button>
          <div className="list-stack" data-testid="session-messages-list">
            {messages.map((message) => (
              <div className="list-card" key={message.id} data-testid={`session-message-${message.id}`}>
                <strong>{message.role}</strong>
                <span>{message.content}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel" data-testid="context-prepare-panel">
          <h2 data-testid="context-prepare-heading">Prepare active context</h2>
          <label htmlFor="query-text" data-testid="query-text-label">Current query</label>
          <textarea
            id="query-text"
            data-testid="query-textarea"
            rows={5}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
          <button
            className="primary-button"
            data-testid="prepare-context-button"
            disabled={busy}
            onClick={handlePrepareContext}
          >
            Sanitize and retrieve
          </button>
          <div className="metrics-grid" data-testid="context-stats-grid">
            <div className="metric-card" data-testid="context-stat-final-messages">
              <span>Active messages</span>
              <strong>{stats.final_messages}</strong>
            </div>
            <div className="metric-card" data-testid="context-stat-reduction-ratio">
              <span>Reduction</span>
              <strong>{reductionPercent}</strong>
            </div>
            <div className="metric-card" data-testid="context-stat-memory-count">
              <span>Injected memories</span>
              <strong>{receipt.injected_memory_count}</strong>
            </div>
          </div>
        </article>
      </section>

      <section className="results-grid" data-testid="context-results-grid">
        <article className="panel" data-testid="sanitized-history-panel">
          <h2 data-testid="sanitized-history-heading">Sanitized history</h2>
          <div className="list-stack" data-testid="sanitized-history-list">
            {(contextResult?.sanitized_history || []).map((message) => (
              <div className="list-card" key={message.id} data-testid={`sanitized-history-${message.id}`}>
                <strong>{message.role}</strong>
                <span>{message.content}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel" data-testid="injected-memory-panel">
          <h2 data-testid="injected-memory-heading">Injected memory</h2>
          <div className="list-stack" data-testid="injected-memory-list">
            {(contextResult?.injected_memories || []).map((memory) => (
              <div className="list-card" key={memory.id} data-testid={`injected-memory-${memory.id}`}>
                <strong>{memory.content}</strong>
                <span>{memory.tags.join(", ")}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel" data-testid="receipt-panel">
          <h2 data-testid="receipt-heading">Receipt</h2>
          <div className="list-stack" data-testid="receipt-list">
            <div className="list-card" data-testid="receipt-retrieval-terms">
              <strong>Retrieval terms</strong>
              <span>{receipt.retrieval_terms?.join(", ") || "none"}</span>
            </div>
            <div className="list-card" data-testid="receipt-before-after">
              <strong>Chars before / after</strong>
              <span>{receipt.estimated_chars_before} / {receipt.estimated_chars_after}</span>
            </div>
            <div className="list-card" data-testid="receipt-removals">
              <strong>Removed duplicates / low signal</strong>
              <span>{stats.removed_duplicates} / {stats.removed_low_signal}</span>
            </div>
          </div>
        </article>
      </section>

      <footer className="status-bar" data-testid="workbench-status-bar">
        <span data-testid="workbench-status-text">{status}</span>
      </footer>
    </main>
  );
};
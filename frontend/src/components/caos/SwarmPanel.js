import { useEffect, useRef, useState } from "react";
import { X, Zap, Play, CheckCircle2, Loader2, Terminal } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * Agent Swarm panel — triggers the Supervisor → Worker(E2B) → Critic pipeline.
 *
 * Streams SSE events from /api/caos/swarm/stream and renders the live state:
 *   - Phase indicator (supervisor / workers / critic / done)
 *   - JSON plan with step descriptions
 *   - Per-step stdout / stderr from the E2B sandbox
 *   - Final answer written by the Critic
 */
export const SwarmPanel = ({ isOpen, onClose }) => {
  const [task, setTask] = useState("");
  const [phase, setPhase] = useState("idle");
  const [plan, setPlan] = useState(null);
  const [steps, setSteps] = useState([]);
  const [finalAnswer, setFinalAnswer] = useState("");
  const [error, setError] = useState("");
  const [running, setRunning] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!isOpen) return undefined;
    const handler = (event) => {
      if (ref.current && !ref.current.contains(event.target)) onClose();
    };
    const esc = (event) => { if (event.key === "Escape") onClose(); };
    document.addEventListener("mousedown", handler);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", handler);
      document.removeEventListener("keydown", esc);
    };
  }, [isOpen, onClose]);

  const reset = () => {
    setPhase("idle"); setPlan(null); setSteps([]); setFinalAnswer(""); setError("");
  };

  const runSwarm = async () => {
    if (!task.trim() || running) return;
    reset();
    setRunning(true);
    setPhase("supervisor");
    try {
      const response = await fetch(`${API}/caos/swarm/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task }),
      });
      if (!response.ok || !response.body) throw new Error(`stream_unavailable_${response.status}`);
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";
        for (const part of parts) {
          const eventLine = part.split("\n").find((l) => l.startsWith("event:"));
          const dataLine = part.split("\n").find((l) => l.startsWith("data:"));
          if (!eventLine || !dataLine) continue;
          const evt = eventLine.slice(6).trim();
          let data;
          try { data = JSON.parse(dataLine.slice(5).trim()); } catch { continue; }
          if (evt === "phase") setPhase(data.phase);
          else if (evt === "plan") setPlan(data.plan);
          else if (evt === "step") setSteps((prev) => [...prev, data]);
          else if (evt === "final") { setFinalAnswer(data.final_answer); setPhase("done"); }
          else if (evt === "error") { setError(data.error || "unknown error"); setPhase("error"); }
        }
      }
    } catch (issue) {
      setError(issue?.message || "Swarm failed");
      setPhase("error");
    } finally {
      setRunning(false);
    }
  };

  if (!isOpen) return null;
  return (
    <div className="swarm-overlay" data-testid="caos-swarm-overlay">
      <div className="swarm-panel" data-testid="caos-swarm-panel" ref={ref}>
        <header className="swarm-header">
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Zap size={16} style={{ color: "#a78bfa" }} />
            <strong>Agent Swarm · Supervisor → E2B Worker → Critic</strong>
          </div>
          <button onClick={onClose} className="swarm-close" data-testid="caos-swarm-close"><X size={16} /></button>
        </header>

        <div className="swarm-task-row">
          <textarea
            className="swarm-task-input"
            data-testid="caos-swarm-task-input"
            placeholder="Give the swarm a task — e.g. 'Compute the first 20 Fibonacci numbers and their ratios' or 'Analyse this CSV: ...'"
            rows={3}
            value={task}
            onChange={(e) => setTask(e.target.value)}
            disabled={running}
          />
          <button
            className="swarm-run-btn"
            data-testid="caos-swarm-run-btn"
            onClick={runSwarm}
            disabled={running || !task.trim()}
          >
            {running ? <Loader2 size={14} className="spin" /> : <Play size={14} />}
            {running ? "Running…" : "Run Swarm"}
          </button>
        </div>

        <div className="swarm-phases" data-testid="caos-swarm-phases">
          {["supervisor", "workers", "critic", "done"].map((name) => (
            <span
              key={name}
              className={`swarm-phase-chip ${phase === name ? "swarm-phase-chip-active" : ""} ${
                ["supervisor", "workers", "critic"].indexOf(phase) > ["supervisor", "workers", "critic"].indexOf(name) || phase === "done" ? "swarm-phase-chip-done" : ""
              }`}
              data-testid={`caos-swarm-phase-${name}`}
            >
              {phase === "done" || (["supervisor", "workers", "critic"].indexOf(phase) > ["supervisor", "workers", "critic"].indexOf(name) && name !== "done")
                ? <CheckCircle2 size={10} />
                : phase === name && running ? <Loader2 size={10} className="spin" /> : null}
              {name === "supervisor" ? "Plan" : name === "workers" ? "Execute" : name === "critic" ? "Review" : "Done"}
            </span>
          ))}
        </div>

        <div className="swarm-body" data-testid="caos-swarm-body">
          {plan ? (
            <section className="swarm-section" data-testid="caos-swarm-plan-section">
              <h4>Plan</h4>
              <p className="swarm-objective" data-testid="caos-swarm-objective">{plan.objective}</p>
              <ul>
                {(plan.steps || []).map((s) => (
                  <li key={s.id} data-testid={`caos-swarm-plan-step-${s.id}`}>
                    <strong>[{s.id}]</strong> {s.description}
                  </li>
                ))}
              </ul>
            </section>
          ) : null}

          {steps.length ? (
            <section className="swarm-section" data-testid="caos-swarm-executed-section">
              <h4><Terminal size={12} style={{ display: "inline", verticalAlign: "-2px" }} /> Execution trace</h4>
              {steps.map((s) => (
                <div className="swarm-step-card" key={s.id} data-testid={`caos-swarm-step-${s.id}`}>
                  <div className="swarm-step-head">
                    <strong>[{s.id}]</strong>
                    <span className={`swarm-step-type-${s.type || "python"}`} data-testid={`caos-swarm-step-type-${s.id}`} style={{
                      display: "inline-block", padding: "2px 7px", marginLeft: 8,
                      fontSize: 10, borderRadius: 999, fontWeight: 600, letterSpacing: 0.4,
                      background: s.type === "tool" ? "rgba(34, 197, 94, 0.18)" : "rgba(99, 102, 241, 0.18)",
                      color: s.type === "tool" ? "#86efac" : "#c7d2fe",
                      border: `1px solid ${s.type === "tool" ? "rgba(34, 197, 94, 0.35)" : "rgba(99, 102, 241, 0.35)"}`,
                      textTransform: "uppercase",
                    }}>
                      {s.type === "tool" ? `tool · ${s.tool_name || "?"}` : "python"}
                    </span>
                    <span style={{ marginLeft: 8 }}>{s.description}</span>
                  </div>
                  {s.stdout ? <pre className="swarm-stdout" data-testid={`caos-swarm-stdout-${s.id}`}>{s.stdout}</pre> : null}
                  {s.stderr ? <pre className="swarm-stderr" data-testid={`caos-swarm-stderr-${s.id}`}>{s.stderr}</pre> : null}
                  {s.error ? <pre className="swarm-stderr" data-testid={`caos-swarm-error-${s.id}`}>Error: {s.error}</pre> : null}
                </div>
              ))}
            </section>
          ) : null}

          {finalAnswer ? (
            <section className="swarm-section swarm-final" data-testid="caos-swarm-final-section">
              <h4>Final answer</h4>
              <p data-testid="caos-swarm-final-answer">{finalAnswer}</p>
            </section>
          ) : null}

          {error ? <div className="swarm-error" data-testid="caos-swarm-error">⚠️ {error}</div> : null}
        </div>
      </div>
    </div>
  );
};

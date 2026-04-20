import { useState } from "react";
import { Volume2 } from "lucide-react";
import { toast } from "sonner";

const LABEL_ORDER = ["Claude", "OpenAI", "Gemini"];
const PROVIDER_ACCENTS = {
  anthropic: { bg: "rgba(250, 204, 21, 0.08)", border: "rgba(250, 204, 21, 0.35)", label: "#fde68a" },
  openai: { bg: "rgba(16, 185, 129, 0.08)", border: "rgba(16, 185, 129, 0.35)", label: "#a7f3d0" },
  gemini: { bg: "rgba(99, 102, 241, 0.08)", border: "rgba(99, 102, 241, 0.35)", label: "#c7d2fe" },
};

/**
 * Renders a side-by-side multi-agent response group.
 * Each agent gets its own column showing provider, model, reply text, and a Read button.
 */
export const MultiAgentMessageGroup = ({ agents, onSpeak, timestamp }) => {
  const [focusedIndex, setFocusedIndex] = useState(null);

  const sorted = [...(agents || [])].sort(
    (a, b) => LABEL_ORDER.indexOf(a.label) - LABEL_ORDER.indexOf(b.label)
  );

  return (
    <article className="multi-agent-group" data-testid="caos-multi-agent-group">
      <div className="multi-agent-topline" data-testid="caos-multi-agent-topline">
        <strong>Multi-Agent · {sorted.length} providers</strong>
        <span data-testid="caos-multi-agent-timestamp">
          {new Date(timestamp || Date.now()).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}
        </span>
      </div>
      <div className="multi-agent-columns" data-testid="caos-multi-agent-columns">
        {sorted.map((agent, index) => {
          const accent = PROVIDER_ACCENTS[agent.provider] || PROVIDER_ACCENTS.anthropic;
          const isFocused = focusedIndex === index;
          return (
            <button
              className={`multi-agent-column ${isFocused ? "multi-agent-column-focused" : ""} ${agent.ok ? "" : "multi-agent-column-failed"}`}
              data-testid={`caos-multi-agent-column-${agent.provider}`}
              key={agent.provider}
              onClick={() => setFocusedIndex(isFocused ? null : index)}
              style={{
                background: accent.bg,
                borderColor: accent.border,
              }}
              type="button"
            >
              <div className="multi-agent-column-header" data-testid={`caos-multi-agent-header-${agent.provider}`}>
                <strong style={{ color: accent.label }}>{agent.label}</strong>
                <span>{agent.model?.replace("-preview", "")}</span>
              </div>
              {agent.ok ? (
                <p className="multi-agent-column-body" data-testid={`caos-multi-agent-body-${agent.provider}`}>
                  {agent.reply}
                </p>
              ) : (
                <p className="multi-agent-column-error" data-testid={`caos-multi-agent-error-${agent.provider}`}>
                  Failed: {agent.error || "unknown error"}
                </p>
              )}
              {agent.ok ? (
                <div className="multi-agent-column-actions">
                  <span
                    className="multi-agent-read"
                    data-testid={`caos-multi-agent-read-${agent.provider}`}
                    onClick={async (event) => {
                      event.stopPropagation();
                      try { await onSpeak(agent.reply); }
                      catch { toast.error("Read aloud failed"); }
                    }}
                    role="button"
                  >
                    <Volume2 size={11} />Read
                  </span>
                  <span className="multi-agent-tokens">{agent.wcw_used_estimate} tok</span>
                </div>
              ) : null}
            </button>
          );
        })}
      </div>
      <p className="multi-agent-hint" data-testid="caos-multi-agent-hint">Tap a column to focus · All three ran in parallel</p>
    </article>
  );
};

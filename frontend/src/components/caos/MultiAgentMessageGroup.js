import { useState } from "react";
import { Volume2, ChevronDown, ChevronUp, Sparkles } from "lucide-react";
import { toast } from "sonner";

const LABEL_ORDER = ["Claude", "OpenAI", "Gemini"];
const PROVIDER_ACCENTS = {
  anthropic: { bg: "rgba(250, 204, 21, 0.08)", border: "rgba(250, 204, 21, 0.35)", label: "#fde68a" },
  openai: { bg: "rgba(16, 185, 129, 0.08)", border: "rgba(16, 185, 129, 0.35)", label: "#a7f3d0" },
  gemini: { bg: "rgba(99, 102, 241, 0.08)", border: "rgba(99, 102, 241, 0.35)", label: "#c7d2fe" },
};

const handleRead = async (event, text, onSpeak) => {
  event.stopPropagation();
  try { await onSpeak(text); }
  catch { toast.error("Read aloud failed"); }
};

/**
 * Renders a synthesized multi-agent reply with collapsible source columns.
 * The Synthesizer (Claude Sonnet 4.5) merges Claude + OpenAI + Gemini into one
 * consolidated answer. The 3 raw columns are tucked behind a "Show sources" toggle.
 */
export const MultiAgentMessageGroup = ({ agents, synthesis, onSpeak, timestamp }) => {
  const [focusedIndex, setFocusedIndex] = useState(null);
  const [sourcesOpen, setSourcesOpen] = useState(false);

  const sorted = [...(agents || [])].sort(
    (a, b) => LABEL_ORDER.indexOf(a.label) - LABEL_ORDER.indexOf(b.label)
  );
  const hasSynthesis = synthesis && synthesis.ok && synthesis.reply;
  const okCount = sorted.filter((a) => a.ok).length;

  return (
    <article className="multi-agent-group" data-testid="caos-multi-agent-group">
      <div className="multi-agent-topline" data-testid="caos-multi-agent-topline">
        <strong>
          <Sparkles size={12} style={{ display: "inline", marginRight: 4, verticalAlign: "-1px" }} />
          {hasSynthesis ? "Synthesized" : "Multi-Agent"} · {okCount}/{sorted.length} providers
        </strong>
        <span data-testid="caos-multi-agent-timestamp">
          {new Date(timestamp || Date.now()).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}
        </span>
      </div>

      {hasSynthesis ? (
        <div
          className="multi-agent-synthesis"
          data-testid="caos-multi-agent-synthesis"
          style={{
            background: "rgba(139, 92, 246, 0.07)",
            border: "1px solid rgba(139, 92, 246, 0.3)",
            borderRadius: 12,
            padding: "14px 16px",
            marginBottom: 10,
          }}
        >
          <p
            className="multi-agent-synthesis-body"
            data-testid="caos-multi-agent-synthesis-body"
            style={{ margin: 0, whiteSpace: "pre-wrap", lineHeight: 1.55 }}
          >
            {synthesis.reply}
          </p>
          <div className="multi-agent-column-actions" style={{ marginTop: 10 }}>
            <span
              className="multi-agent-read"
              data-testid="caos-multi-agent-synthesis-read"
              onClick={(event) => handleRead(event, synthesis.reply, onSpeak)}
              role="button"
            >
              <Volume2 size={11} />Read
            </span>
            <span className="multi-agent-tokens">Claude Sonnet 4.5 · merged from {synthesis.source_labels?.join(" · ") || "agents"}</span>
          </div>
        </div>
      ) : null}

      <button
        type="button"
        className="multi-agent-sources-toggle"
        data-testid="caos-multi-agent-sources-toggle"
        onClick={() => setSourcesOpen((open) => !open)}
        style={{
          background: "transparent",
          border: "none",
          color: "rgba(226, 232, 240, 0.75)",
          cursor: "pointer",
          display: "inline-flex",
          alignItems: "center",
          gap: 6,
          padding: "4px 0",
          fontSize: 12,
        }}
      >
        {sourcesOpen ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
        {sourcesOpen ? "Hide sources" : `Show sources (${sorted.length})`}
      </button>

      {sourcesOpen ? (
        <div className="multi-agent-columns" data-testid="caos-multi-agent-columns">
          {sorted.map((agent, index) => {
            const accent = PROVIDER_ACCENTS[agent.provider] || PROVIDER_ACCENTS.anthropic;
            const isFocused = focusedIndex === index;
            const replyPreview = (agent.reply || "").slice(0, 180);
            return (
              <button
                className={`multi-agent-column ${isFocused ? "multi-agent-column-focused" : ""} ${agent.ok ? "" : "multi-agent-column-failed"}`}
                data-testid={`caos-multi-agent-column-${agent.provider}`}
                key={agent.provider}
                onClick={() => setFocusedIndex(isFocused ? null : index)}
                style={{ background: accent.bg, borderColor: accent.border }}
                type="button"
              >
                <div className="multi-agent-column-header" data-testid={`caos-multi-agent-header-${agent.provider}`}>
                  <div className="multi-agent-column-titleblock" data-testid={`caos-multi-agent-titleblock-${agent.provider}`}>
                    <strong style={{ color: accent.label }}>{agent.label}</strong>
                    <span data-testid={`caos-multi-agent-subtitle-${agent.provider}`}>{agent.model?.replace("-preview", "")}</span>
                  </div>
                  <span data-testid={`caos-multi-agent-expand-state-${agent.provider}`}>{isFocused ? "Expanded" : "Preview"}</span>
                </div>
                {agent.ok ? (
                  <>
                    <p className={`multi-agent-column-body ${isFocused ? "multi-agent-column-body-expanded" : ""}`} data-testid={`caos-multi-agent-body-${agent.provider}`}>
                    {agent.reply}
                    </p>
                    <p className="multi-agent-column-preview-hint" data-testid={`caos-multi-agent-preview-hint-${agent.provider}`}>
                      {isFocused ? "Tap again to collapse this card." : `${replyPreview}${(agent.reply || "").length > 180 ? "…" : ""}`}
                    </p>
                  </>
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
                      onClick={(event) => handleRead(event, agent.reply, onSpeak)}
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
      ) : null}

      <p className="multi-agent-hint" data-testid="caos-multi-agent-hint">
        {hasSynthesis
          ? "One answer, merged from 3 parallel agents · Tap Show sources to compare"
          : "Tap a column to focus · All three ran in parallel"}
      </p>
    </article>
  );
};

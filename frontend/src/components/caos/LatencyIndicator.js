import { AlertTriangle, Clock, Zap } from "lucide-react";

const formatSeconds = (ms) => {
  const numeric = Number(ms) || 0;
  if (numeric < 1000) return `${numeric}ms`;
  return `${(numeric / 1000).toFixed(1)}s`;
};

const pickTier = (ms) => {
  if (ms < 2000) return { label: "fast", color: "#34d399", Icon: Zap };
  if (ms < 5000) return { label: "normal", color: "#fbbf24", Icon: Clock };
  return { label: "slow", color: "#f87171", Icon: AlertTriangle };
};

/**
 * Per-message latency badge. Accepts a receipt with any of:
 *  - total_ms (preferred, from backend instrumentation)
 *  - t_total (server-side latency_breakdown)
 *  - inference_ms fallback
 */
export const LatencyIndicator = ({ receipt }) => {
  const totalMs = receipt?.total_ms
    || receipt?.t_total
    || (receipt?.latency_breakdown?.t_total)
    || (receipt?.inference_ms)
    || 0;
  if (!totalMs) return null;

  const { color, Icon, label } = pickTier(totalMs);

  return (
    <span
      className="latency-indicator"
      data-testid={`caos-latency-indicator-${receipt?.id || receipt?.assistant_message_id || "na"}`}
      title={`Response time: ${totalMs}ms (${label})`}
    >
      <Icon size={11} style={{ color }} />
      <span data-testid="caos-latency-value">{formatSeconds(totalMs)}</span>
    </span>
  );
};

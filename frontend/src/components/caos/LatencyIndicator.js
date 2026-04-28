import { AlertTriangle, Clock, Zap } from "lucide-react";
import { useMemo, useState } from "react";

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

const pickTotalMs = (receipt) => receipt?.total_ms
  || receipt?.latency_ms
  || receipt?.t_total
  || receipt?.latency_breakdown?.t_total
  || receipt?.latency_budget?.actual_ms
  || receipt?.inference_ms
  || 0;

const normalizeTimingRows = (value) => {
  if (!value) return [];
  if (Array.isArray(value)) {
    return value
      .map((row) => ({
        label: row?.phase || row?.event || row?.name || "phase",
        ms: Number(row?.duration_ms || row?.ms || row?.total_ms || 0),
      }))
      .filter((row) => row.ms > 0);
  }
  if (typeof value === "object") {
    return Object.entries(value)
      .map(([label, ms]) => ({ label, ms: Number(ms) || 0 }))
      .filter((row) => row.ms > 0);
  }
  return [];
};

const formatHydration = (policy) => policy?.mode || policy?.hydration_mode || "standard";
const formatProactivity = (policy) => policy?.primary_intent || policy?.intent || "direct";

/**
 * Per-message latency badge. Accepts a receipt with any of:
 *  - total_ms / latency_ms (preferred)
 *  - latency_budget.actual_ms / t_total / latency_breakdown.t_total
 *  - inference_ms fallback
 *
 * If TurnTrace fields are present and the viewer is admin, the popover shows a
 * compact diagnostic breakdown. Non-admin users receive a plain-language
 * explanation only; raw trace internals stay behind the admin boundary.
 */
export const LatencyIndicator = ({ receipt, className = "", isAdmin = false }) => {
  const [open, setOpen] = useState(false);
  const totalMs = pickTotalMs(receipt);
  const topContributors = useMemo(() => {
    const phaseRows = normalizeTimingRows(receipt?.phase_timings);
    const categoryRows = normalizeTimingRows(receipt?.latency_category_totals);
    return (phaseRows.length ? phaseRows : categoryRows)
      .sort((a, b) => b.ms - a.ms)
      .slice(0, 5);
  }, [receipt]);

  if (!totalMs) return null;

  const { color, Icon, label } = pickTier(totalMs);
  const budget = receipt?.latency_budget || {};
  const hasTraceDetails = Boolean(
    topContributors.length
      || receipt?.latency_trace
      || receipt?.latency_category_totals
      || receipt?.hydration_policy
      || receipt?.proactivity_policy,
  );
  const showTraceDetails = isAdmin && hasTraceDetails;
  const toolsUsed = Array.isArray(receipt?.tools_used) ? receipt.tools_used : [];
  const traceId = receipt?.id || receipt?.assistant_message_id || "na";

  return (
    <span style={{ position: "relative", display: "inline-flex" }}>
      <button
        aria-expanded={open}
        aria-haspopup="dialog"
        className={`latency-indicator ${className}`.trim()}
        data-testid={`caos-latency-indicator-${traceId}`}
        onClick={() => setOpen((value) => !value)}
        title={`Response time: ${totalMs}ms (${label})`}
        type="button"
        style={{
          alignItems: "center",
          background: "rgba(15, 23, 42, 0.74)",
          border: "1px solid rgba(148, 163, 184, 0.16)",
          borderRadius: 999,
          color: "inherit",
          cursor: "pointer",
          display: "inline-flex",
          gap: 6,
          padding: "4px 8px",
        }}
      >
        <Icon size={11} style={{ color }} />
        <span data-testid="caos-latency-value">{formatSeconds(totalMs)}</span>
      </button>
      {open ? (
        <span
          className="latency-popover"
          data-testid={`caos-latency-popover-${traceId}`}
          role="dialog"
          style={{
            background: "rgba(7, 15, 31, 0.98)",
            border: "1px solid rgba(148, 163, 184, 0.22)",
            borderRadius: 16,
            boxShadow: "0 24px 60px rgba(0, 0, 0, 0.34)",
            color: "#eff6ff",
            display: "grid",
            gap: 8,
            left: 0,
            minWidth: 280,
            padding: 12,
            position: "absolute",
            top: "calc(100% + 8px)",
            zIndex: 50,
          }}
        >
          <strong>Response latency — {formatSeconds(totalMs)}</strong>
          {showTraceDetails ? (
            <>
              <span>
                Budget: {budget?.target_ms ? formatSeconds(budget.target_ms) : "unclassified"}
                {budget?.exceeded ? ` — exceeded by ${formatSeconds(budget.over_by_ms || Math.max(0, totalMs - (budget.target_ms || 0)))}` : ""}
              </span>
              {topContributors.length ? (
                <span style={{ display: "grid", gap: 4 }}>
                  <strong style={{ fontSize: "0.78rem" }}>Top contributors</strong>
                  {topContributors.map((row) => (
                    <span key={`${row.label}-${row.ms}`}>{row.label} — {formatSeconds(row.ms)}</span>
                  ))}
                </span>
              ) : null}
              <span>Hydration: {formatHydration(receipt?.hydration_policy)}</span>
              <span>Proactivity: {formatProactivity(receipt?.proactivity_policy)}</span>
              <span>Tools: {toolsUsed.length ? `${toolsUsed.length} · ${toolsUsed.join(", ")}` : "none recorded"}</span>
              {Array.isArray(receipt?.latency_trace) && receipt.latency_trace.length ? (
                <details>
                  <summary>Full trace</summary>
                  <pre style={{ maxHeight: 220, overflow: "auto", whiteSpace: "pre-wrap" }}>{JSON.stringify(receipt.latency_trace, null, 2)}</pre>
                </details>
              ) : null}
            </>
          ) : (
            <span>This response took longer because extra processing may have been used for your request.</span>
          )}
        </span>
      ) : null}
    </span>
  );
};

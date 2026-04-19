import { Brain, FileText, X } from "lucide-react";


export const InspectorPanel = ({ continuity, isOpen, latestReceipt, memorySurface, onClose }) => {
  if (!isOpen) return null;

  const continuityCount = (latestReceipt?.selected_summary_ids?.length || 0) + (latestReceipt?.selected_seed_ids?.length || 0);
  const workerCount = latestReceipt?.selected_worker_ids?.length || 0;
  const tokenSourceLabel = latestReceipt?.token_source === "provider_usage" ? "provider usage" : "tokenizer fallback";

  return (
    <aside className="inspector-panel" data-testid="caos-inspector-panel">
      <div className="inspector-header" data-testid="caos-inspector-header">
        <strong data-testid="caos-inspector-title">Inspector</strong>
        <button className="drawer-close-button" data-testid="caos-inspector-close-button" onClick={onClose}>
          <X size={14} />
        </button>
      </div>

      <section className="inspector-card" data-testid="caos-inspector-receipt-card">
        <div className="context-card-heading">
          <Brain size={16} />
          <h2 data-testid="caos-inspector-receipt-heading">Why this reply fits</h2>
        </div>
        <div className="context-metric-grid" data-testid="caos-inspector-receipt-grid">
          <div className="context-metric" data-testid="caos-inspector-receipt-reduction">
            <span>Trimmed</span>
            <strong>{Math.round((latestReceipt?.reduction_ratio || 0) * 100)}%</strong>
          </div>
          <div className="context-metric" data-testid="caos-inspector-receipt-lane">
            <span>Lane</span>
            <strong>{latestReceipt?.lane || "general"}</strong>
          </div>
          <div className="context-metric" data-testid="caos-inspector-receipt-continuity-count">
            <span>Continuity</span>
            <strong>{continuityCount}</strong>
          </div>
          <div className="context-metric" data-testid="caos-inspector-receipt-worker-count">
            <span>Workers</span>
            <strong>{workerCount}</strong>
          </div>
        </div>
        <div className="context-metric" data-testid="caos-inspector-receipt-runtime">
          <span>Runtime</span>
          <strong>{latestReceipt?.provider || "openai"} · {latestReceipt?.model || "gpt-5.2"}</strong>
        </div>
        <div className="context-metric" data-testid="caos-inspector-receipt-terms">
          <span>Used for recall</span>
          <strong>{latestReceipt?.retrieval_terms?.join(", ") || "No turn yet"}</strong>
        </div>
        <div className="context-metric" data-testid="caos-inspector-receipt-bins">
          <span>Subject bins</span>
          <strong>{latestReceipt?.subject_bins?.join(", ") || "No bins selected"}</strong>
        </div>
        <div className="context-metric" data-testid="caos-inspector-rehydration-order">
          <span>Rehydration order</span>
          <strong>{latestReceipt?.rehydration_order?.join(" → ") || "thread_history → lane_continuity → personal_facts → structured_memory"}</strong>
        </div>
        <div className="context-metric-grid context-metric-grid-compact" data-testid="caos-inspector-packet-grid">
          <div className="context-metric" data-testid="caos-inspector-packet-context-chars">
            <span>Packet chars</span>
            <strong>{latestReceipt?.estimated_context_chars || 0}</strong>
          </div>
          <div className="context-metric" data-testid="caos-inspector-packet-memory-count">
            <span>Memories</span>
            <strong>{latestReceipt?.selected_memory_ids?.length || 0}</strong>
          </div>
          <div className="context-metric" data-testid="caos-inspector-personal-facts-count">
            <span>Facts</span>
            <strong>{latestReceipt?.personal_facts_count || 0}</strong>
          </div>
          <div className="context-metric" data-testid="caos-inspector-global-cache-count">
            <span>Global cache</span>
            <strong>{latestReceipt?.global_cache_count || 0}</strong>
          </div>
        </div>
        <div className="context-metric-grid context-metric-grid-compact" data-testid="caos-inspector-token-grid">
          <div className="context-metric" data-testid="caos-inspector-active-context-tokens">
            <span>ARC tokens</span>
            <strong>{latestReceipt?.active_context_tokens || 0}</strong>
          </div>
          <div className="context-metric" data-testid="caos-inspector-prompt-tokens">
            <span>Sent</span>
            <strong>{latestReceipt?.prompt_tokens || 0}</strong>
          </div>
          <div className="context-metric" data-testid="caos-inspector-completion-tokens">
            <span>Received</span>
            <strong>{latestReceipt?.completion_tokens || 0}</strong>
          </div>
          <div className="context-metric" data-testid="caos-inspector-thread-total-tokens">
            <span>Thread total</span>
            <strong>{latestReceipt?.session_total_tokens || 0}</strong>
          </div>
        </div>
        <div className="context-metric-grid context-metric-grid-compact" data-testid="caos-inspector-token-breakdown-grid">
          <div className="context-metric" data-testid="caos-inspector-history-tokens">
            <span>History</span>
            <strong>{latestReceipt?.history_tokens || 0}</strong>
          </div>
          <div className="context-metric" data-testid="caos-inspector-memory-tokens">
            <span>Memory</span>
            <strong>{latestReceipt?.memory_tokens || 0}</strong>
          </div>
          <div className="context-metric" data-testid="caos-inspector-continuity-tokens">
            <span>Continuity</span>
            <strong>{latestReceipt?.continuity_tokens || 0}</strong>
          </div>
          <div className="context-metric" data-testid="caos-inspector-global-cache-tokens">
            <span>Global cache</span>
            <strong>{latestReceipt?.global_cache_tokens || 0}</strong>
          </div>
          <div className="context-metric" data-testid="caos-inspector-token-source">
            <span>Meter source</span>
            <strong>{tokenSourceLabel}</strong>
          </div>
        </div>
        <div className="context-metric" data-testid="caos-inspector-global-bin-status">
          <span>Global bin</span>
          <strong>{latestReceipt?.global_bin_status || "empty"}</strong>
        </div>
      </section>

      <section className="inspector-card" data-testid="caos-inspector-continuity-card">
        <div className="context-card-heading">
          <Brain size={16} />
          <h2 data-testid="caos-inspector-continuity-heading">Carried forward</h2>
        </div>
        <div className="context-metric" data-testid="caos-inspector-continuity-depth">
          <span>Thread depth</span>
          <strong>{continuity?.lineage_depth || 0}</strong>
        </div>
        <div className="context-list-item" data-testid="caos-inspector-continuity-summary">
          {continuity?.latest_summary?.summary || "No continuity summary yet."}
        </div>
        <div className="context-list-item" data-testid="caos-inspector-continuity-seed">
          {continuity?.latest_seed?.seed_text || "No continuity seed yet."}
        </div>
      </section>

      <section className="inspector-card" data-testid="caos-inspector-retention-card">
        <div className="context-card-heading">
          <Brain size={16} />
          <h2 data-testid="caos-inspector-retention-heading">Retention reasoning</h2>
        </div>
        <div className="context-metric-grid context-metric-grid-compact" data-testid="caos-inspector-retention-grid">
          <div className="context-metric" data-testid="caos-inspector-retained-count">
            <span>Kept</span>
            <strong>{latestReceipt?.retained_message_count || 0}</strong>
          </div>
          <div className="context-metric" data-testid="caos-inspector-dropped-count">
            <span>Dropped</span>
            <strong>{latestReceipt?.dropped_message_count || 0}</strong>
          </div>
          <div className="context-metric" data-testid="caos-inspector-compressed-count">
            <span>Compressed</span>
            <strong>{latestReceipt?.compressed_message_count || 0}</strong>
          </div>
          <div className="context-metric" data-testid="caos-inspector-reused-count">
            <span>Reused</span>
            <strong>{(latestReceipt?.reused_memory_count || 0) + (latestReceipt?.reused_continuity_count || 0)}</strong>
          </div>
          <div className="context-metric" data-testid="caos-inspector-budget-trim-count">
            <span>Budget trim</span>
            <strong>{latestReceipt?.budget_trimmed_count || 0}</strong>
          </div>
        </div>
        <div className="context-metric-grid context-metric-grid-compact" data-testid="caos-inspector-budget-grid">
          <div className="context-metric" data-testid="caos-inspector-history-budget-limit">
            <span>History budget</span>
            <strong>{latestReceipt?.history_budget_tokens || 0}</strong>
          </div>
          <div className="context-metric" data-testid="caos-inspector-history-budget-before">
            <span>Before</span>
            <strong>{latestReceipt?.history_tokens_before_budget || 0}</strong>
          </div>
          <div className="context-metric" data-testid="caos-inspector-history-budget-after">
            <span>After</span>
            <strong>{latestReceipt?.history_tokens_after_budget || 0}</strong>
          </div>
        </div>
        <div className="context-list" data-testid="caos-inspector-retention-explanation-list">
          {(latestReceipt?.retention_explanation || []).map((line, index) => (
            <div className="context-list-item" data-testid={`caos-inspector-retention-explanation-${index}`} key={`retention-${index}`}>
              {line}
            </div>
          ))}
        </div>
        <div className="context-list" data-testid="caos-inspector-retention-detail-list">
          {(latestReceipt?.dropped_messages || []).slice(0, 2).map((item) => (
            <div className="context-list-item" data-testid={`caos-inspector-dropped-item-${item.id}`} key={`dropped-${item.id}`}>
              <strong>Dropped · {item.reason}</strong>
              <span>{item.excerpt}</span>
            </div>
          ))}
          {(latestReceipt?.compressed_messages || []).slice(0, 2).map((item) => (
            <div className="context-list-item" data-testid={`caos-inspector-compressed-item-${item.id}`} key={`compressed-${item.id}`}>
              <strong>Compressed</strong>
              <span>{item.excerpt}</span>
            </div>
          ))}
          {(latestReceipt?.budget_trimmed_messages || []).slice(0, 2).map((item) => (
            <div className="context-list-item" data-testid={`caos-inspector-budget-trim-item-${item.id}`} key={`trimmed-${item.id}`}>
              <strong>Trimmed for budget</strong>
              <span>{item.excerpt}</span>
            </div>
          ))}
          {(latestReceipt?.reused_continuity || []).slice(0, 2).map((item) => (
            <div className="context-list-item" data-testid={`caos-inspector-reused-item-${item.id}`} key={`reused-${item.kind}-${item.id}`}>
              <strong>Reused · {item.kind}</strong>
              <span>{item.excerpt}</span>
            </div>
          ))}
        </div>
      </section>

      {memorySurface.length ? (
        <section className="inspector-card" data-testid="caos-inspector-memory-card">
          <div className="context-card-heading">
            <FileText size={16} />
            <h2 data-testid="caos-inspector-memory-heading">Memory in play</h2>
          </div>
          <div className="context-list" data-testid="caos-inspector-memory-list">
            {memorySurface.map((memory) => (
              <div className="context-list-item" data-testid={`caos-inspector-memory-item-${memory.id}`} key={memory.id}>
                <strong>{memory.bin_name || "general"}</strong>
                <span>{memory.content}</span>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </aside>
  );
};
import { Brain, FileText, X } from "lucide-react";


export const InspectorPanel = ({ continuity, isOpen, latestReceipt, memorySurface, onClose }) => {
  if (!isOpen) return null;

  const continuityCount = (latestReceipt?.selected_summary_ids?.length || 0) + (latestReceipt?.selected_seed_ids?.length || 0);

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
        <div className="context-metric" data-testid="caos-inspector-receipt-reduction">
          <span>Context trimmed</span>
          <strong>{Math.round((latestReceipt?.reduction_ratio || 0) * 100)}%</strong>
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
        <div className="context-metric" data-testid="caos-inspector-receipt-continuity-count">
          <span>Continuity packets</span>
          <strong>{continuityCount}</strong>
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
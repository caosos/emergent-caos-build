import { FolderKanban, X } from "lucide-react";


export const ArtifactsDrawer = ({ artifacts, isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="drawer-overlay" data-testid="caos-artifacts-drawer-overlay">
      <aside className="drawer-shell" data-testid="caos-artifacts-drawer">
        <div className="drawer-header">
          <div className="context-card-heading">
            <FolderKanban size={16} />
            <h2 data-testid="caos-artifacts-drawer-heading">Artifacts</h2>
          </div>
          <button className="drawer-close-button" data-testid="caos-artifacts-drawer-close-button" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <section className="drawer-section" data-testid="caos-artifacts-receipts-section">
          <h3 data-testid="caos-artifacts-receipts-heading">Receipts</h3>
          {(artifacts?.receipts || []).slice(0, 8).map((receipt) => (
            <div className="drawer-list-item" data-testid={`caos-artifact-receipt-${receipt.id}`} key={receipt.id}>
              {receipt.provider}:{receipt.model} • reduction {Math.round((receipt.reduction_ratio || 0) * 100)}%
            </div>
          ))}
        </section>

        <section className="drawer-section" data-testid="caos-artifacts-summaries-section">
          <h3 data-testid="caos-artifacts-summaries-heading">Summaries</h3>
          {(artifacts?.summaries || []).slice(0, 6).map((summary) => (
            <div className="drawer-list-item" data-testid={`caos-artifact-summary-${summary.id}`} key={summary.id}>
              {summary.summary}
            </div>
          ))}
        </section>

        <section className="drawer-section" data-testid="caos-artifacts-seeds-section">
          <h3 data-testid="caos-artifacts-seeds-heading">Seeds</h3>
          {(artifacts?.seeds || []).slice(0, 6).map((seed) => (
            <div className="drawer-list-item" data-testid={`caos-artifact-seed-${seed.id}`} key={seed.id}>
              {(seed.topics || []).join(", ") || seed.seed_text}
            </div>
          ))}
        </section>
      </aside>
    </div>
  );
};
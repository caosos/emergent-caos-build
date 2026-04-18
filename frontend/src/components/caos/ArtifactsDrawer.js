import { useState } from "react";
import { FolderKanban, X } from "lucide-react";


export const ArtifactsDrawer = ({ artifacts, files, isOpen, onClose, onSaveLink, onUploadFile }) => {
  const [label, setLabel] = useState("");
  const [url, setUrl] = useState("");
  if (!isOpen) return null;

  const grouped = {
    files: files.filter((item) => item.kind === "file"),
    photos: files.filter((item) => item.kind === "photo"),
    links: files.filter((item) => item.kind === "link"),
  };

  const recentReceipts = (artifacts?.receipts || []).slice(0, 8);
  const recentSummaries = (artifacts?.summaries || []).slice(0, 6);
  const recentSeeds = (artifacts?.seeds || []).slice(0, 6);

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

        <section className="drawer-section" data-testid="caos-files-section">
          <h3 data-testid="caos-files-heading">Files / Photos / Links</h3>
          <label className="message-action-button" data-testid="caos-files-upload-button">
            Upload file
            <input data-testid="caos-files-upload-input" hidden type="file" onChange={(event) => onUploadFile(event.target.files?.[0])} />
          </label>
          <div className="drawer-link-form">
            <input data-testid="caos-link-label-input" placeholder="Link label" value={label} onChange={(event) => setLabel(event.target.value)} />
            <input data-testid="caos-link-url-input" placeholder="https://..." value={url} onChange={(event) => setUrl(event.target.value)} />
            <button
              className="message-action-button"
              data-testid="caos-save-link-button"
              onClick={() => {
                onSaveLink(url, label);
                setLabel("");
                setUrl("");
              }}
            >
              Save link
            </button>
          </div>
          {["files", "photos", "links"].map((section) => (
            <div className="drawer-section-block" data-testid={`caos-${section}-section`} key={section}>
              <h3>{section}</h3>
              {(grouped[section] || []).slice(0, 8).map((item) => (
                <div className="drawer-list-item" data-testid={`caos-${section}-item-${item.id}`} key={item.id}>
                  {item.url ? <a href={item.url} rel="noreferrer" target="_blank">{item.name}</a> : item.name}
                </div>
              ))}
            </div>
          ))}
        </section>

        <section className="drawer-section" data-testid="caos-artifacts-receipts-section">
          <h3 data-testid="caos-artifacts-receipts-heading">Receipts</h3>
          {recentReceipts.map((receipt) => (
            <div className="drawer-list-item drawer-list-item-rich" data-testid={`caos-artifact-receipt-${receipt.id}`} key={receipt.id}>
              <strong data-testid={`caos-artifact-receipt-title-${receipt.id}`}>{receipt.provider}:{receipt.model}</strong>
              <span data-testid={`caos-artifact-receipt-reduction-${receipt.id}`}>Reduction {Math.round((receipt.reduction_ratio || 0) * 100)}%</span>
              <span data-testid={`caos-artifact-receipt-bins-${receipt.id}`}>Bins: {receipt.subject_bins?.join(", ") || "none"}</span>
              <span data-testid={`caos-artifact-receipt-memory-count-${receipt.id}`}>Memories {receipt.selected_memory_ids?.length || 0} · Continuity {(receipt.selected_summary_ids?.length || 0) + (receipt.selected_seed_ids?.length || 0)}</span>
            </div>
          ))}
        </section>

        <section className="drawer-section" data-testid="caos-artifacts-summaries-section">
          <h3 data-testid="caos-artifacts-summaries-heading">Summaries</h3>
          {recentSummaries.map((summary) => (
            <div className="drawer-list-item drawer-list-item-rich" data-testid={`caos-artifact-summary-${summary.id}`} key={summary.id}>
              <strong data-testid={`caos-artifact-summary-bins-${summary.id}`}>{summary.subject_bins?.join(", ") || "general"}</strong>
              <span>{summary.summary}</span>
            </div>
          ))}
        </section>

        <section className="drawer-section" data-testid="caos-artifacts-seeds-section">
          <h3 data-testid="caos-artifacts-seeds-heading">Seeds</h3>
          {recentSeeds.map((seed) => (
            <div className="drawer-list-item drawer-list-item-rich" data-testid={`caos-artifact-seed-${seed.id}`} key={seed.id}>
              <strong data-testid={`caos-artifact-seed-bins-${seed.id}`}>{seed.subject_bins?.join(", ") || "general"}</strong>
              <span>{(seed.topics || []).join(", ") || seed.seed_text}</span>
              <span>{seed.seed_text}</span>
            </div>
          ))}
        </section>
      </aside>
    </div>
  );
};
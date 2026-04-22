import { useEffect, useState } from "react";
import { FolderKanban, X } from "lucide-react";


export const ArtifactsDrawer = ({ artifacts, files, initialFilter, isOpen, links = [], onClose, onSaveLink, onUploadFile }) => {
  const [activeTab, setActiveTab] = useState("files");
  const [label, setLabel] = useState("");
  const [url, setUrl] = useState("");

  // Respect the submenu choice from the account dropdown ("Files" / "Photos" / "Links").
  useEffect(() => {
    if (!isOpen || !initialFilter) return;
    setActiveTab(initialFilter);
  }, [initialFilter, isOpen]);
  if (!isOpen) return null;

  const grouped = {
    files: files.filter((item) => item.kind === "file"),
    photos: files.filter((item) => item.kind === "photo"),
  };

  const recentReceipts = (artifacts?.receipts || []).slice(0, 8);
  const recentSummaries = (artifacts?.summaries || []).slice(0, 6);
  const recentSeeds = (artifacts?.seeds || []).slice(0, 6);
  const tabs = [
    { id: "files", label: "Files", count: grouped.files.length },
    { id: "photos", label: "Photos", count: grouped.photos.length },
    { id: "links", label: "Links", count: links.length },
    { id: "receipts", label: "Receipts", count: recentReceipts.length },
    { id: "summaries", label: "Summaries", count: recentSummaries.length },
    { id: "seeds", label: "Seeds", count: recentSeeds.length },
  ];

  return (
    <div className="drawer-overlay" data-testid="caos-artifacts-drawer-overlay" onClick={onClose}>
      <aside className="drawer-shell" data-testid="caos-artifacts-drawer" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <div className="context-card-heading">
            <FolderKanban size={16} />
            <h2 data-testid="caos-artifacts-drawer-heading">Artifacts</h2>
          </div>
          <button className="drawer-close-button" data-testid="caos-artifacts-drawer-close-button" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <div className="drawer-stats-row" data-testid="caos-artifacts-stats-row">
          <div className="drawer-stat-card" data-testid="caos-artifacts-files-stat">
            <span>Stored items</span>
            <strong>{grouped.files.length + grouped.photos.length + links.length}</strong>
          </div>
          <div className="drawer-stat-card" data-testid="caos-artifacts-receipts-stat">
            <span>Receipts</span>
            <strong>{recentReceipts.length}</strong>
          </div>
          <div className="drawer-stat-card" data-testid="caos-artifacts-memory-stat">
            <span>Memory artifacts</span>
            <strong>{recentSummaries.length + recentSeeds.length}</strong>
          </div>
        </div>

        <div className="drawer-tab-row" data-testid="caos-artifacts-tab-row">
          {tabs.map((tab) => (
            <button
              className={`drawer-tab-button ${activeTab === tab.id ? "drawer-tab-button-active" : ""}`}
              data-testid={`caos-artifacts-tab-${tab.id}`}
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              type="button"
            >
              <span>{tab.label}</span>
              <strong>{tab.count}</strong>
            </button>
          ))}
        </div>

        <section className="drawer-section" data-testid="caos-files-section" hidden={activeTab !== "files"}>
          <h3 data-testid="caos-files-heading">Files</h3>
          <label className="message-action-button" data-testid="caos-files-upload-button">
            Upload file
            <input data-testid="caos-files-upload-input" hidden type="file" onChange={(event) => onUploadFile(event.target.files?.[0])} />
          </label>
          {grouped.files.length === 0 ? <div className="drawer-empty">No files yet.</div> : null}
          {grouped.files.map((item) => (
            <div className="drawer-list-item" data-testid={`caos-files-item-${item.id}`} key={item.id}>
              {item.url ? <a href={item.url} rel="noreferrer" target="_blank">{item.name}</a> : item.name}
            </div>
          ))}
        </section>

        <section className="drawer-section" data-testid="caos-photos-section" hidden={activeTab !== "photos"}>
          <h3 data-testid="caos-photos-heading">Photos</h3>
          <label className="message-action-button" data-testid="caos-photos-upload-button">
            Upload photo
            <input data-testid="caos-photos-upload-input" accept="image/*" hidden type="file" onChange={(event) => onUploadFile(event.target.files?.[0])} />
          </label>
          {grouped.photos.length === 0 ? <div className="drawer-empty">No photos yet.</div> : null}
          <div className="drawer-photo-grid">
            {grouped.photos.map((item) => (
              <a className="drawer-photo-tile" data-testid={`caos-photos-item-${item.id}`} href={item.url} key={item.id} rel="noreferrer" target="_blank" title={item.name}>
                <img alt={item.name} loading="lazy" src={item.url} />
              </a>
            ))}
          </div>
        </section>

        <section className="drawer-section" data-testid="caos-links-section" hidden={activeTab !== "links"}>
          <h3 data-testid="caos-links-heading">Links</h3>
          <div className="drawer-link-form">
            <input data-testid="caos-link-label-input" placeholder="Link label (optional)" value={label} onChange={(event) => setLabel(event.target.value)} />
            <input data-testid="caos-link-url-input" placeholder="https://..." value={url} onChange={(event) => setUrl(event.target.value)} />
            <button
              className="message-action-button"
              data-testid="caos-save-link-button"
              onClick={async () => {
                const saved = await onSaveLink(url, label);
                if (!saved) return;
                setLabel("");
                setUrl("");
              }}
            >
              Save link
            </button>
          </div>
          {links.length === 0 ? <div className="drawer-empty" data-testid="caos-links-empty">No links yet. URLs you send in chat will appear here automatically.</div> : null}
          {links.map((item) => (
            <div className="drawer-list-item drawer-list-item-rich drawer-link-item" data-testid={`caos-links-item-${item.id}`} key={item.id}>
              <a data-testid={`caos-links-item-link-${item.id}`} href={item.url} rel="noreferrer" target="_blank">{item.label || item.host || item.url}</a>
              <span data-testid={`caos-links-item-url-${item.id}`}>{item.url}</span>
              <div className="drawer-link-meta" data-testid={`caos-links-item-meta-${item.id}`}>
                <span data-testid={`caos-links-item-source-${item.id}`}>{item.source === "auto" ? "Auto-detected" : item.source === "legacy" ? "Legacy" : "Saved manually"}</span>
                <span data-testid={`caos-links-item-count-${item.id}`}>Mentioned {item.mention_count || 1}×</span>
              </div>
            </div>
          ))}
        </section>

        <section className="drawer-section" data-testid="caos-artifacts-receipts-section" hidden={activeTab !== "receipts"}>
          <h3 data-testid="caos-artifacts-receipts-heading">Receipts</h3>
          {recentReceipts.map((receipt) => (
            <div className="drawer-list-item drawer-list-item-rich" data-testid={`caos-artifact-receipt-${receipt.id}`} key={receipt.id}>
              <strong data-testid={`caos-artifact-receipt-title-${receipt.id}`}>{receipt.provider}:{receipt.model}</strong>
              <span data-testid={`caos-artifact-receipt-reduction-${receipt.id}`}>Reduction {Math.round((receipt.reduction_ratio || 0) * 100)}%</span>
              <span data-testid={`caos-artifact-receipt-bins-${receipt.id}`}>Bins: {receipt.subject_bins?.join(", ") || "none"}</span>
              <span data-testid={`caos-artifact-receipt-memory-count-${receipt.id}`}>Memories {receipt.selected_memory_ids?.length || 0} · Continuity {(receipt.selected_summary_ids?.length || 0) + (receipt.selected_seed_ids?.length || 0)}</span>
              <span data-testid={`caos-artifact-receipt-retention-${receipt.id}`}>Kept {receipt.retained_message_count || 0} · Dropped {receipt.dropped_message_count || 0} · Compressed {receipt.compressed_message_count || 0} · Trimmed {receipt.budget_trimmed_count || 0}</span>
              <span data-testid={`caos-artifact-receipt-global-cache-${receipt.id}`}>Global cache {receipt.global_cache_count || 0} · {receipt.global_bin_status || "empty"}</span>
              <span data-testid={`caos-artifact-receipt-explanation-${receipt.id}`}>{receipt.retention_explanation?.[0] || "Retention reasoning will appear after the next turn."}</span>
            </div>
          ))}
        </section>

        <section className="drawer-section" data-testid="caos-artifacts-summaries-section" hidden={activeTab !== "summaries"}>
          <h3 data-testid="caos-artifacts-summaries-heading">Summaries</h3>
          {recentSummaries.map((summary) => (
            <div className="drawer-list-item drawer-list-item-rich" data-testid={`caos-artifact-summary-${summary.id}`} key={summary.id}>
              <strong data-testid={`caos-artifact-summary-bins-${summary.id}`}>{summary.subject_bins?.join(", ") || "general"}</strong>
              <span>{summary.summary}</span>
            </div>
          ))}
        </section>

        <section className="drawer-section" data-testid="caos-artifacts-seeds-section" hidden={activeTab !== "seeds"}>
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
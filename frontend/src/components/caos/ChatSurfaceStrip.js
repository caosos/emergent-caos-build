import { FolderOpen, Radar, Search, Workflow } from "lucide-react";


export const ChatSurfaceStrip = ({ latestReceipt, onOpenArtifacts, onOpenInspector, onOpenSearch }) => {
  const continuityCount = (latestReceipt?.selected_summary_ids?.length || 0) + (latestReceipt?.selected_seed_ids?.length || 0);

  return (
    <div className="chat-surface-strip" data-testid="caos-chat-surface-strip">
      <div className="chat-surface-chip" data-testid="caos-chat-surface-wcw-chip">
        <span>Working packet</span>
        <strong>{latestReceipt?.estimated_context_chars || latestReceipt?.estimated_chars_after || 0} chars</strong>
      </div>
      <div className="chat-surface-chip" data-testid="caos-chat-surface-lane-chip">
        <span>Lane</span>
        <strong>{latestReceipt?.lane || "general"}</strong>
      </div>
      <div className="chat-surface-chip" data-testid="caos-chat-surface-continuity-chip">
        <span>Continuity</span>
        <strong>{continuityCount} packets</strong>
      </div>
      <div className="chat-surface-actions" data-testid="caos-chat-surface-actions">
        <button className="surface-strip-button" data-testid="caos-chat-surface-search-button" onClick={onOpenSearch} type="button">
          <Search size={14} />
          <span>Search</span>
        </button>
        <button className="surface-strip-button" data-testid="caos-chat-surface-inspector-button" onClick={onOpenInspector} type="button">
          <Radar size={14} />
          <span>Context</span>
        </button>
        <button className="surface-strip-button" data-testid="caos-chat-surface-files-button" onClick={onOpenArtifacts} type="button">
          <FolderOpen size={14} />
          <span>Files</span>
        </button>
        <div className="surface-strip-button surface-strip-passive" data-testid="caos-chat-surface-hydration-chip">
          <Workflow size={14} />
          <span>{latestReceipt?.subject_bins?.length || 0} bins</span>
        </div>
      </div>
    </div>
  );
};
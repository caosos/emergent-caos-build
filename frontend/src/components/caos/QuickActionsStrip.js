export const QuickActionsStrip = ({ onContinueThread, onOpenArtifacts }) => {
  return (
    <div className="quick-actions-strip" data-testid="caos-quick-actions-strip">
      <button className="quick-action-pill" data-testid="caos-quick-action-create-image">Create Image</button>
      <button className="quick-action-pill" data-testid="caos-quick-action-upload-file" onClick={onOpenArtifacts}>Files</button>
      <button className="quick-action-pill" data-testid="caos-quick-action-capture-screen">Capture</button>
      <button className="quick-action-pill" data-testid="caos-quick-action-continue-thread" onClick={onContinueThread}>Continue</button>
    </div>
  );
};
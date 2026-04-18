import { SendHorizontal } from "lucide-react";
import { useState } from "react";


export const Composer = ({ busy, onSend, status }) => {
  const [draft, setDraft] = useState("");

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!draft.trim() || busy) return;
    onSend(draft);
    setDraft("");
  };

  return (
    <form className="composer-shell" data-testid="caos-composer-shell" onSubmit={handleSubmit}>
      <label className="composer-label" htmlFor="caos-draft" data-testid="caos-composer-label">
        Active prompt
      </label>
      <div className="composer-row">
        <textarea
          data-testid="caos-composer-textarea"
          id="caos-draft"
          placeholder="Type into the real CAOS shell..."
          rows={3}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
        <button className="primary-shell-button composer-send" data-testid="caos-composer-send-button" disabled={busy || !draft.trim()}>
          <SendHorizontal size={16} />
          <span>Send</span>
        </button>
      </div>
      <div className="composer-status" data-testid="caos-composer-status">{status}</div>
    </form>
  );
};
import { Mic, Paperclip, SendHorizontal } from "lucide-react";
import { useState } from "react";


export const Composer = ({ busy, onSend, onTranscribe, onUploadFile, status }) => {
  const [draft, setDraft] = useState("");
  const [recording, setRecording] = useState(false);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!draft.trim() || busy) return;
    onSend(draft);
    setDraft("");
  };

  const handleUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    await onUploadFile(file);
    event.target.value = "";
  };

  const handleRecord = async () => {
    if (recording) return;
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    const chunks = [];
    setRecording(true);
    recorder.ondataavailable = (event) => chunks.push(event.data);
    recorder.onstop = async () => {
      const blob = new Blob(chunks, { type: recorder.mimeType || "audio/webm" });
      const text = await onTranscribe(blob);
      setDraft((previous) => [previous, text].filter(Boolean).join(" ").trim());
      setRecording(false);
      stream.getTracks().forEach((track) => track.stop());
    };
    recorder.start();
    setTimeout(() => recorder.state !== "inactive" && recorder.stop(), 5000);
  };

  return (
    <form className="composer-shell" data-testid="caos-composer-shell" onSubmit={handleSubmit}>
      <label className="composer-label" htmlFor="caos-draft" data-testid="caos-composer-label">
        Active prompt
      </label>
      <div className="composer-row">
        <label className="message-action-button composer-upload" data-testid="caos-composer-upload-button">
          <Paperclip size={16} />
          <span>Attach</span>
          <input data-testid="caos-composer-upload-input" hidden type="file" onChange={handleUpload} />
        </label>
        <textarea
          data-testid="caos-composer-textarea"
          id="caos-draft"
          placeholder="Type into the real CAOS shell..."
          rows={3}
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
        />
        <button className="message-action-button composer-mic" data-testid="caos-composer-mic-button" onClick={handleRecord} type="button">
          <Mic size={16} />
          <span>{recording ? "Recording" : "Mic"}</span>
        </button>
        <button className="primary-shell-button composer-send" data-testid="caos-composer-send-button" disabled={busy || !draft.trim()}>
          <SendHorizontal size={16} />
          <span>Send</span>
        </button>
      </div>
      <div className="composer-status" data-testid="caos-composer-status">{status}</div>
    </form>
  );
};
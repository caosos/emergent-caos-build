import { Mic, Paperclip, SendHorizontal, Square, Volume2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";


const joinDraft = (base, addition) => [base, addition].filter(Boolean).join(" ").replace(/\s+/g, " ").trim();
const MIN_ROWS = 1;
const MAX_ROWS = 6;
const LINE_HEIGHT = 22;


export const Composer = ({ busy, draft, lastAssistantMessage, onDraftChange, onSend, onSpeak, onTranscribe, onTranscribeChunk, onUploadFile, status, voiceSettings }) => {
  const [recording, setRecording] = useState(false);
  const [liveStatus, setLiveStatus] = useState("");
  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const initialDraftRef = useRef("");
  const liveTranscriptRef = useRef("");
  const textareaRef = useRef(null);

  useEffect(() => {
    const node = textareaRef.current;
    if (!node) return;
    node.style.height = "auto";
    const next = Math.min(MAX_ROWS * LINE_HEIGHT, Math.max(MIN_ROWS * LINE_HEIGHT, node.scrollHeight));
    node.style.height = `${next}px`;
    node.style.overflowY = node.scrollHeight > MAX_ROWS * LINE_HEIGHT ? "auto" : "hidden";
  }, [draft]);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!draft.trim() || busy) return;
    onSend(draft);
    onDraftChange("");
  };

  const handleUpload = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    await onUploadFile(file);
    event.target.value = "";
  };

  const stopRecording = () => {
    if (recorderRef.current?.state !== "inactive") {
      recorderRef.current.stop();
    }
  };

  const mergeLiveChunk = (incoming) => {
    const nextText = incoming.trim();
    if (!nextText) return liveTranscriptRef.current;
    const previous = liveTranscriptRef.current.trim();
    if (!previous) return nextText;
    if (previous.endsWith(nextText)) return previous;
    if (nextText.startsWith(previous)) return nextText;
    return `${previous} ${nextText}`.replace(/\s+/g, " ").trim();
  };

  const showStatus = status
    && !/^Loaded \d+ saved sessions\.$/.test(status)
    && status !== "CAOS replied with session-scoped context."
    && status !== "No sessions yet. Start a thread to begin the CAOS shell.";

  const handleRecord = async () => {
    if (recording) {
      stopRecording();
      return;
    }
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new MediaRecorder(stream);
    recorderRef.current = recorder;
    streamRef.current = stream;
    chunksRef.current = [];
    initialDraftRef.current = draft;
    liveTranscriptRef.current = "";
    setLiveStatus(`Listening with ${voiceSettings.stt_primary_model}...`);
    setRecording(true);
    recorder.ondataavailable = async (event) => {
      if (!event.data?.size) return;
      chunksRef.current.push(event.data);
      try {
        const response = await onTranscribeChunk(event.data, liveTranscriptRef.current || initialDraftRef.current);
        const merged = mergeLiveChunk(response.text || "");
        liveTranscriptRef.current = merged;
        onDraftChange(joinDraft(initialDraftRef.current, merged));
        setLiveStatus(`Streaming with ${response.model_used}${response.fallback_used ? " (fallback)" : ""}`);
      } catch {
        setLiveStatus("Streaming unavailable — final transcript will still be added.");
      }
    };
    recorder.onstop = async () => {
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
      const response = await onTranscribe(blob);
      const text = response.text || "";
      liveTranscriptRef.current = text;
      onDraftChange(joinDraft(initialDraftRef.current, text));
      setLiveStatus("");
      setRecording(false);
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      recorderRef.current = null;
    };
    recorder.start(1400);
  };

  const handleReadLastAssistant = async () => {
    if (!lastAssistantMessage?.content) return;
    await onSpeak(lastAssistantMessage.content);
  };

  return (
    <form className="composer-shell" data-testid="caos-composer-shell" onSubmit={handleSubmit}>
      <div className="composer-row">
        <label className="message-action-button composer-upload" data-testid="caos-composer-upload-button">
          <Paperclip size={16} />
          <input data-testid="caos-composer-upload-input" hidden type="file" onChange={handleUpload} />
        </label>
        <button
          className="message-action-button composer-read-last"
          data-testid="caos-composer-read-last-button"
          disabled={!lastAssistantMessage?.content}
          onClick={handleReadLastAssistant}
          type="button"
        >
          <Volume2 size={16} />
        </button>
        <textarea
          data-testid="caos-composer-textarea"
          id="caos-draft"
          placeholder="Ask anything... and switch models mid chat with no problem!"
          ref={textareaRef}
          rows={MIN_ROWS}
          value={draft}
          onChange={(event) => onDraftChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              handleSubmit(event);
            }
          }}
        />
        <button className="message-action-button composer-mic" data-testid="caos-composer-mic-button" onClick={handleRecord} type="button">
          {recording ? <Square size={16} /> : <Mic size={16} />}
        </button>
        <button className="primary-shell-button composer-send" data-testid="caos-composer-send-button" disabled={busy || !draft.trim()}>
          <SendHorizontal size={16} />
        </button>
      </div>
      {recording && liveStatus ? <div className="composer-live-status" data-testid="caos-composer-live-status">{liveStatus}</div> : null}
      {showStatus ? <div className="composer-status" data-testid="caos-composer-status">{status}</div> : null}
    </form>
  );
};
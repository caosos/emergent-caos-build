import { Mic, Paperclip, Plus, SendHorizontal, Square, Volume2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";


const joinDraft = (base, addition) => [base, addition].filter(Boolean).join(" ").replace(/\s+/g, " ").trim();
const MIN_ROWS = 1;
const MAX_ROWS = 6;
const LINE_HEIGHT = 22;


export const Composer = ({ busy, draft, lastAssistantMessage, onDraftChange, onSend, onSpeak, onTranscribe, onTranscribeChunk, onUploadFile, status, voiceSettings }) => {
  const [recording, setRecording] = useState(false);
  const [liveStatus, setLiveStatus] = useState("");
  const [liveTranscript, setLiveTranscript] = useState("");
  const [transientStatus, setTransientStatus] = useState("");
  const [thoughtStash, setThoughtStash] = useState(() => {
    try { return JSON.parse(localStorage.getItem("caos_thought_stash") || "[]"); }
    catch { return []; }
  });
  const recorderRef = useRef(null);
  const streamRef = useRef(null);
  const chunksRef = useRef([]);
  const initialDraftRef = useRef("");
  const liveTranscriptRef = useRef("");
  const textareaRef = useRef(null);

  // Persist the stash so thoughts survive reloads — the whole point is to
  // not lose a half-formed idea while you walk away.
  useEffect(() => {
    localStorage.setItem("caos_thought_stash", JSON.stringify(thoughtStash));
  }, [thoughtStash]);

  // Mirror the shell status into a transient local state that auto-clears
  // after 4s so banners never stick around longer than the user expects.
  useEffect(() => {
    if (!status) return undefined;
    setTransientStatus(status);
    const timer = setTimeout(() => setTransientStatus(""), 4000);
    return () => clearTimeout(timer);
  }, [status]);

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
    if (busy) return;
    // Combine stashed thoughts + current draft into one compound message.
    const compound = [...thoughtStash.map((t) => t.text), draft].filter((s) => s.trim()).join("\n\n");
    if (!compound.trim()) return;
    onSend(compound);
    onDraftChange("");
    setThoughtStash([]);
  };

  const stashCurrentThought = () => {
    const text = draft.trim();
    if (!text) return;
    setThoughtStash((prev) => [...prev, { id: Date.now(), text }]);
    onDraftChange("");
    textareaRef.current?.focus();
  };

  const removeThought = (id) => {
    setThoughtStash((prev) => prev.filter((t) => t.id !== id));
  };

  const clearStash = () => setThoughtStash([]);

  const handleUpload = async (event) => {
    const picked = Array.from(event.target.files || []);
    event.target.value = "";
    if (!picked.length) return;
    const capped = picked.slice(0, 10);
    if (picked.length > 10) toast.message(`Attached first 10 of ${picked.length} files`);
    let okCount = 0;
    for (const file of capped) {
      try {
        await onUploadFile(file);
        okCount += 1;
      } catch (error) {
        toast.error(`Failed to upload ${file.name}: ${(error?.message || "unknown").slice(0, 60)}`);
      }
    }
    if (okCount > 0) toast.success(`Attached ${okCount} file${okCount === 1 ? "" : "s"} — the AI can now see them`);
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

  const showStatus = transientStatus
    && !/^Loaded \d+ saved sessions\.$/.test(transientStatus)
    && transientStatus !== "CAOS replied with session-scoped context."
    && transientStatus !== "No sessions yet. Start a thread to begin the CAOS shell.";

  const handleRecord = async () => {
    if (recording) {
      stopRecording();
      return;
    }
    if (!navigator.mediaDevices?.getUserMedia) {
      toast.error("Microphone not available in this browser");
      return;
    }
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (error) {
      if (error?.name === "NotAllowedError") {
        toast.error("Microphone permission denied — allow it in browser settings");
      } else if (error?.name === "NotFoundError") {
        toast.error("No microphone found");
      } else {
        toast.error(`Mic error: ${(error?.message || "unknown").slice(0, 60)}`);
      }
      return;
    }
    let recorder;
    try {
      recorder = new MediaRecorder(stream);
    } catch (error) {
      toast.error(`Recorder unsupported: ${(error?.message || "unknown").slice(0, 60)}`);
      stream.getTracks().forEach((track) => track.stop());
      return;
    }
    recorderRef.current = recorder;
    streamRef.current = stream;
    chunksRef.current = [];
    initialDraftRef.current = draft;
    liveTranscriptRef.current = "";
    setLiveTranscript("");
    setLiveStatus(`Listening with ${voiceSettings.stt_primary_model}...`);
    setRecording(true);
    toast.success("Recording — tap mic again to stop", { duration: 2000 });
    recorder.ondataavailable = async (event) => {
      if (!event.data?.size) return;
      chunksRef.current.push(event.data);
      // WebM chunks aren't independently decodable — send cumulative blob so each
      // transcription call gets a valid audio stream from t=0 to now.
      const cumulative = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
      try {
        const response = await onTranscribeChunk(cumulative, liveTranscriptRef.current || initialDraftRef.current);
        const merged = mergeLiveChunk(response.text || "");
        liveTranscriptRef.current = merged;
        setLiveTranscript(merged);
        onDraftChange(joinDraft(initialDraftRef.current, merged));
        setLiveStatus(`Streaming with ${response.model_used}${response.fallback_used ? " (fallback)" : ""}`);
      } catch {
        setLiveStatus("Streaming unavailable — final transcript will still be added.");
      }
    };
    recorder.onstop = async () => {
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
      try {
        const response = await onTranscribe(blob);
        const text = response.text || liveTranscriptRef.current || "";
        liveTranscriptRef.current = text;
        setLiveTranscript(text);
        onDraftChange(joinDraft(initialDraftRef.current, text));
        setLiveStatus("");
      } catch {
        onDraftChange(joinDraft(initialDraftRef.current, liveTranscriptRef.current));
        setLiveStatus("Transcription failed — using live stream capture.");
      }
      setRecording(false);
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      recorderRef.current = null;
    };
    recorder.start(1400);
  };

  const handleReadLastAssistant = async () => {
    if (!lastAssistantMessage?.content) {
      toast.error("No assistant reply to read yet");
      return;
    }
    try {
      await onSpeak(lastAssistantMessage.content);
    } catch (error) {
      toast.error(`Read aloud failed: ${(error?.message || "unknown").slice(0, 60)}`);
    }
  };

  return (
    <form className="composer-shell" data-testid="caos-composer-shell" onSubmit={handleSubmit}>
      {thoughtStash.length > 0 ? (
        <div className="composer-thought-stash" data-testid="caos-composer-thought-stash">
          <div className="composer-thought-stash-header">
            <span>{thoughtStash.length} thought{thoughtStash.length === 1 ? "" : "s"} queued · send together</span>
            <button
              type="button"
              data-testid="caos-composer-thought-stash-clear"
              onClick={clearStash}
              className="composer-thought-stash-clear"
            >Clear</button>
          </div>
          {thoughtStash.map((thought, index) => (
            <div key={thought.id} className="composer-thought-chip" data-testid={`caos-composer-thought-chip-${index}`}>
              <span className="composer-thought-chip-num">{index + 1}</span>
              <p>{thought.text}</p>
              <button
                type="button"
                className="composer-thought-chip-remove"
                data-testid={`caos-composer-thought-remove-${index}`}
                onClick={() => removeThought(thought.id)}
                aria-label="remove thought"
              >×</button>
            </div>
          ))}
        </div>
      ) : null}
      <div className="composer-row">
        <label className="message-action-button composer-upload" data-testid="caos-composer-upload-button">
          <Paperclip size={16} />
          <input data-testid="caos-composer-upload-input" hidden multiple type="file" onChange={handleUpload} />
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
        <button
          className="message-action-button composer-stash-btn"
          data-testid="caos-composer-stash-button"
          disabled={!draft.trim()}
          onClick={stashCurrentThought}
          title="Stash this thought and start another (Ctrl+Shift+Enter)"
          type="button"
        >
          <Plus size={16} />
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
            if (event.key === "Enter" && event.ctrlKey && event.shiftKey) {
              event.preventDefault();
              stashCurrentThought();
              return;
            }
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              handleSubmit(event);
            }
          }}
        />
        <button className={`message-action-button composer-mic ${recording ? "composer-mic-recording" : ""}`} data-testid="caos-composer-mic-button" onClick={handleRecord} type="button">
          {recording ? <Square size={16} /> : <Mic size={16} />}
        </button>
        <button className="primary-shell-button composer-send" data-testid="caos-composer-send-button" disabled={busy || (!draft.trim() && thoughtStash.length === 0)}>
          <SendHorizontal size={16} />
        </button>
      </div>
      {recording && liveStatus ? <div className="composer-live-status" data-testid="caos-composer-live-status">{liveStatus}</div> : null}
      {recording && liveTranscript ? <div className="composer-live-transcript" data-testid="caos-composer-live-transcript">{liveTranscript}</div> : null}
      {showStatus ? <div className="composer-status" data-testid="caos-composer-status">{transientStatus}</div> : null}
    </form>
  );
};
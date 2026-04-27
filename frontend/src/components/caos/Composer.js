import { Mic, Paperclip, Plus, SendHorizontal, Square, Volume2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";


const joinDraft = (base, addition) => [base, addition].filter(Boolean).join(" ").replace(/\s+/g, " ").trim();
const MIN_ROWS = 1;
const MAX_ROWS = 4;
const LINE_HEIGHT = 22;


export const Composer = ({ busy, draft, lastAssistantMessage, onDraftChange, onSend, onSpeak, onTranscribe, onTranscribeChunk, onUploadFile, status, voiceSettings }) => {
  const [recording, setRecording] = useState(false);
  const [liveStatus, setLiveStatus] = useState("");
  const [liveTranscript, setLiveTranscript] = useState("");
  const [transientStatus, setTransientStatus] = useState("");
  const [pendingAttachments, setPendingAttachments] = useState([]);  // visible chips so user SEES attachments before send
  const [thoughtStash, setThoughtStash] = useState(() => {
    try { return JSON.parse(localStorage.getItem("caos_thought_stash") || "[]"); }
    catch { return []; }
  });
  // Composer read-aloud uses the BROWSER's native speechSynthesis (not API) —
  // so it plays instantly, is free, and user can stop it on second click.
  const [nativeSpeaking, setNativeSpeaking] = useState(false);
  const [nativeVoices, setNativeVoices] = useState([]);
  const [nativeVoiceURI, setNativeVoiceURI] = useState(() => localStorage.getItem("caos_native_tts_voice") || "");
  const [voicePickerOpen, setVoicePickerOpen] = useState(false);
  const voicePickerRef = useRef(null);
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
    setPendingAttachments([]);  // clear attachment chips after send (bug fix Apr 22)
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
        const uploaded = await onUploadFile(file);
        okCount += 1;
        // Show an immediate visible chip so the user SEES the file is attached
        const previewUrl = uploaded?.url || (file.type?.startsWith("image/") ? URL.createObjectURL(file) : null);
        setPendingAttachments((prev) => [...prev, {
          id: uploaded?.id || `local-${Date.now()}-${file.name}`,
          name: file.name,
          isImage: (file.type || "").startsWith("image/"),
          url: previewUrl,
        }]);
      } catch (error) {
        toast.error(`Failed to upload ${file.name}: ${(error?.message || "unknown").slice(0, 60)}`);
      }
    }
    if (okCount > 0) toast.success(`Attached ${okCount} file${okCount === 1 ? "" : "s"} — the AI can now see them`);
  };

  const removePendingAttachment = (id) => {
    setPendingAttachments((prev) => prev.filter((a) => a.id !== id));
  };

  const stopRecording = () => {
    if (recorderRef.current && recorderRef.current.state !== "inactive") {
      // Immediately reflect "stopping/processing" in the UI before the async
      // recorder.stop() round-trip + transcription network call. Without this
      // the user clicked the stop button and saw ~half a second of dead air.
      setRecording(false);
      setTransientStatus("Processing transcription…");
      recorderRef.current.stop();
    }
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
      // Base44 approach: Add audio constraints for better quality
      stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          sampleRate: 16000, // Whisper native sample rate
        }
      });
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
    setRecording(true);
    toast.success("Recording — tap mic again to stop", { duration: 2000 });
    
    // Base44 approach: Collect chunks, transcribe ONCE on stop (no streaming)
    recorder.ondataavailable = (event) => {
      if (event.data?.size) {
        chunksRef.current.push(event.data);
      }
    };
    
    recorder.onstop = async () => {
      const blob = new Blob(chunksRef.current, { type: recorder.mimeType || "audio/webm" });
      // Guard against truly empty captures (very fast click-click, or mic muted at OS level).
      if (!blob.size || blob.size < 1024) {
        toast.error("Recording was too short or empty — try holding the mic and speaking for 1-2 seconds");
        setRecording(false);
        streamRef.current?.getTracks().forEach((track) => track.stop());
        streamRef.current = null;
        recorderRef.current = null;
        return;
      }
      try {
        const response = await onTranscribe(blob);
        const transcriptText = (response?.text || "").trim();
        // If Whisper returned empty text, the mic captured silence / unintelligible audio.
        // Preserve the user's existing draft instead of wiping it, and tell them why.
        if (!transcriptText) {
          toast.error("I didn't catch any speech — try speaking closer to the mic, in a quieter spot, or for longer");
          setRecording(false);
          streamRef.current?.getTracks().forEach((track) => track.stop());
          streamRef.current = null;
          recorderRef.current = null;
          return;
        }
        const newDraft = initialDraftRef.current
          ? `${initialDraftRef.current} ${transcriptText}`
          : transcriptText;
        onDraftChange(newDraft);
        toast.success(`Transcribed: "${transcriptText.slice(0, 60)}${transcriptText.length > 60 ? "..." : ""}"`, { duration: 2200 });
      } catch (error) {
        const status = error?.response?.status;
        const detail = error?.response?.data?.detail || error?.message || "unknown";
        toast.error(`Transcription failed${status ? ` (HTTP ${status})` : ""}: ${String(detail).slice(0, 100)}`);
        console.error("STT error:", { status, detail, error });
      }
      setRecording(false);
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      recorderRef.current = null;
    };
    
    // Base44 approach: Start recording with NO timeslice (single blob on stop)
    recorder.start();
  };

  // Load Chrome's native voices (async on first call) + subscribe to changes.
  useEffect(() => {
    if (typeof window === "undefined" || !window.speechSynthesis) return undefined;
    const refresh = () => {
      const voices = window.speechSynthesis.getVoices() || [];
      setNativeVoices(voices);
    };
    refresh();
    window.speechSynthesis.addEventListener("voiceschanged", refresh);
    return () => window.speechSynthesis.removeEventListener("voiceschanged", refresh);
  }, []);

  // Close voice-picker on click-outside + Escape.
  useEffect(() => {
    if (!voicePickerOpen) return undefined;
    const onDown = (event) => {
      if (voicePickerRef.current && !voicePickerRef.current.contains(event.target)) {
        setVoicePickerOpen(false);
      }
    };
    const onEsc = (event) => { if (event.key === "Escape") setVoicePickerOpen(false); };
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onEsc);
    };
  }, [voicePickerOpen]);

  // Cancel any in-flight native speech when this component unmounts.
  useEffect(() => () => {
    try { window.speechSynthesis?.cancel(); } catch { /* no-op */ }
  }, []);

  const handleReadLastAssistant = () => {
    const synth = typeof window !== "undefined" ? window.speechSynthesis : null;
    if (!synth) {
      toast.error("This browser has no native TTS");
      return;
    }
    // Second click → stop.
    if (nativeSpeaking) {
      synth.cancel();
      setNativeSpeaking(false);
      return;
    }
    if (!lastAssistantMessage?.content) {
      toast.error("No assistant reply to read yet");
      return;
    }
    try { synth.cancel(); } catch { /* no-op */ }
    const utter = new SpeechSynthesisUtterance(lastAssistantMessage.content);
    const picked = nativeVoices.find((v) => v.voiceURI === nativeVoiceURI);
    if (picked) utter.voice = picked;
    utter.onend = () => setNativeSpeaking(false);
    utter.onerror = () => setNativeSpeaking(false);
    setNativeSpeaking(true);
    synth.speak(utter);
  };

  const pickNativeVoice = (voiceURI) => {
    setNativeVoiceURI(voiceURI);
    localStorage.setItem("caos_native_tts_voice", voiceURI);
    setVoicePickerOpen(false);
    toast.success(`Voice: ${nativeVoices.find((v) => v.voiceURI === voiceURI)?.name || "default"}`, { duration: 1500 });
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
      {pendingAttachments.length > 0 ? (
        <div className="composer-pending-attachments" data-testid="caos-composer-pending-attachments">
          {pendingAttachments.map((att) => (
            <div className="composer-pending-attachment-chip" data-testid={`caos-composer-pending-attachment-${att.id}`} key={att.id}>
              {att.isImage && att.url ? (
                <img alt={att.name} className="composer-pending-attachment-thumb" src={att.url} />
              ) : (
                <span className="composer-pending-attachment-icon"><Paperclip size={12} /></span>
              )}
              <span className="composer-pending-attachment-name" title={att.name}>{att.name}</span>
              <button
                aria-label="Remove attachment"
                className="composer-pending-attachment-remove"
                data-testid={`caos-composer-pending-attachment-remove-${att.id}`}
                onClick={() => removePendingAttachment(att.id)}
                type="button"
              >×</button>
            </div>
          ))}
        </div>
      ) : null}
      <div className="composer-row">
        <label className="message-action-button composer-upload" data-testid="caos-composer-upload-button" title="Attach a file or photo" aria-label="Attach a file or photo">
          <Paperclip size={16} />
          <input data-testid="caos-composer-upload-input" hidden multiple type="file" onChange={handleUpload} />
        </label>
        <div className="composer-read-last-wrap" ref={voicePickerRef} style={{ position: "relative", display: "inline-flex" }}>
        <button
          aria-label={nativeSpeaking ? "Stop reading" : (lastAssistantMessage?.content ? "Read last CAOS reply aloud (right-click to choose voice)" : "No reply yet to read")}
          className={`message-action-button composer-read-last ${nativeSpeaking ? "composer-read-last-speaking" : ""}`}
          data-testid="caos-composer-read-last-button"
          disabled={!lastAssistantMessage?.content && !nativeSpeaking}
          onClick={handleReadLastAssistant}
          onContextMenu={(event) => { event.preventDefault(); setVoicePickerOpen((v) => !v); }}
          title={nativeSpeaking ? "Stop reading" : "Read last CAOS reply aloud (right-click: pick voice)"}
          type="button"
        >
          <Volume2 size={16} />
        </button>
        {voicePickerOpen ? (
          <div className="composer-voice-picker" data-testid="caos-composer-voice-picker" style={{ position: "absolute", bottom: "calc(100% + 8px)", left: 0, zIndex: 80, minWidth: 220, maxHeight: 280, overflowY: "auto", background: "rgba(12, 12, 20, 0.98)", border: "1px solid rgba(167, 139, 250, 0.45)", borderRadius: 12, padding: 6, boxShadow: "0 14px 40px rgba(0,0,0,0.55)" }}>
            <div style={{ fontSize: 10.5, letterSpacing: "0.14em", textTransform: "uppercase", color: "rgba(167, 139, 250, 0.85)", padding: "6px 8px 8px" }}>
              Browser voice ({nativeVoices.length})
            </div>
            {nativeVoices.length === 0 ? (
              <div style={{ padding: "8px 10px", fontSize: 12, color: "rgba(148, 163, 184, 0.7)" }}>No voices found in this browser.</div>
            ) : (
              nativeVoices.map((v) => (
                <button
                  key={v.voiceURI}
                  data-testid={`caos-composer-voice-option-${v.voiceURI}`}
                  onClick={() => pickNativeVoice(v.voiceURI)}
                  style={{ display: "block", width: "100%", textAlign: "left", padding: "7px 10px", fontSize: 12.5, borderRadius: 8, border: "none", cursor: "pointer", background: v.voiceURI === nativeVoiceURI ? "rgba(167, 139, 250, 0.22)" : "transparent", color: "rgba(226, 232, 240, 0.95)" }}
                >
                  {v.name} <span style={{ opacity: 0.55 }}>· {v.lang}</span>{v.default ? <span style={{ opacity: 0.55 }}> · default</span> : null}
                </button>
              ))
            )}
          </div>
        ) : null}
        </div>
        <button
          aria-label="Stash current thought to queue"
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
        <button
          aria-label={recording ? "Stop recording" : "Record voice message"}
          className={`message-action-button composer-mic ${recording ? "composer-mic-recording" : ""}`}
          data-testid="caos-composer-mic-button"
          onClick={handleRecord}
          title={recording ? "Stop recording" : "Hold to dictate — speech-to-text"}
          type="button"
        >
          {recording ? <Square size={16} /> : <Mic size={16} />}
        </button>
        <button
          aria-label="Send message"
          className="primary-shell-button composer-send"
          data-testid="caos-composer-send-button"
          disabled={busy || (!draft.trim() && thoughtStash.length === 0)}
          title="Send message (Enter)"
        >
          <SendHorizontal size={16} />
        </button>
      </div>
      {recording ? (
        <div className="composer-equalizer" data-testid="caos-composer-equalizer" aria-hidden="true">
          <span /><span /><span /><span /><span /><span /><span /><span />
          <span className="composer-equalizer-dot" />
          <span className="composer-equalizer-label">Recording</span>
        </div>
      ) : null}
      {showStatus ? <div className="composer-status" data-testid="caos-composer-status">{transientStatus}</div> : null}
    </form>
  );
};
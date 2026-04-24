import { useEffect, useRef, useState, useCallback } from "react";
import { Mic, X, Volume2, Loader } from "lucide-react";
import { toast } from "sonner";

import "./VoiceFirstMode.css";

/**
 * Voice-First Mode — full-duplex hands-free conversation with Aria.
 *
 * Cycle: LISTEN → on 2.5s silence → STOP → TRANSCRIBE → SEND → wait for reply →
 * SPEAK reply → back to LISTEN. Exit anytime with Esc, the X button, or by
 * saying nothing for 30s (auto-timeout).
 *
 * NEVER mutates the existing one-shot mic / TTS UI — this is a separate
 * fullscreen overlay. Closing it restores the normal interface untouched.
 *
 * Accessibility: ARIA live regions announce state changes; keyboard exit;
 * high-contrast pulse + status text for low-vision users.
 */
const SILENCE_THRESHOLD = 0.012;       // RMS amplitude below this = "silence"
const SILENCE_DURATION_MS = 2500;       // 2.5 s of quiet ends the utterance
const MIN_UTTERANCE_MS = 800;           // ignore anything shorter
const MAX_UTTERANCE_MS = 30_000;        // 30 s hard cap
const IDLE_TIMEOUT_MS = 60_000;         // exit after 60 s of total silence

const STATES = {
  IDLE: "idle",
  LISTENING: "listening",
  TRANSCRIBING: "transcribing",
  THINKING: "thinking",
  SPEAKING: "speaking",
  ERROR: "error",
};

export const VoiceFirstMode = ({
  onClose,
  onSendMessage,
  speakText,
  transcribeAudio,
  lastAssistantMessage,
  busy,
}) => {
  const [state, setState] = useState(STATES.IDLE);
  const [statusText, setStatusText] = useState("Tap or wait — I'll start listening");
  const [transcript, setTranscript] = useState("");

  const mediaRecorderRef = useRef(null);
  const audioStreamRef = useRef(null);
  const audioContextRef = useRef(null);
  const analyzerRef = useRef(null);
  const chunksRef = useRef([]);
  const silenceTimerRef = useRef(null);
  const utteranceStartRef = useRef(0);
  const idleTimerRef = useRef(null);
  const lastSpokenIdRef = useRef(null);
  const cancelledRef = useRef(false);
  const stopRecordingRef = useRef(null);

  // ---------------- Audio capture + silence detection ------------------------

  const startListening = useCallback(async () => {
    if (cancelledRef.current) return;
    setState(STATES.LISTENING);
    setStatusText("Listening… speak naturally");
    setTranscript("");

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      audioStreamRef.current = stream;

      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      audioContextRef.current = ctx;
      const source = ctx.createMediaStreamSource(stream);
      const analyzer = ctx.createAnalyser();
      analyzer.fftSize = 1024;
      source.connect(analyzer);
      analyzerRef.current = analyzer;

      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;
      chunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) chunksRef.current.push(event.data);
      };
      recorder.start();
      utteranceStartRef.current = Date.now();

      // Idle exit timer — if no speech detected at all in 60s, exit gracefully
      idleTimerRef.current = setTimeout(() => {
        setStatusText("No speech detected — exiting voice mode");
        setTimeout(onClose, 1200);
      }, IDLE_TIMEOUT_MS);

      // Silence detection loop using analyzer RMS
      const buffer = new Float32Array(analyzer.fftSize);
      let speechDetected = false;

      const tick = () => {
        if (!analyzerRef.current || cancelledRef.current) return;
        analyzer.getFloatTimeDomainData(buffer);
        let sum = 0;
        for (let i = 0; i < buffer.length; i++) sum += buffer[i] * buffer[i];
        const rms = Math.sqrt(sum / buffer.length);

        const elapsed = Date.now() - utteranceStartRef.current;

        if (rms > SILENCE_THRESHOLD) {
          if (!speechDetected) {
            speechDetected = true;
            // user started speaking — clear the idle timer
            if (idleTimerRef.current) {
              clearTimeout(idleTimerRef.current);
              idleTimerRef.current = null;
            }
            setStatusText("Hearing you…");
          }
          // reset silence timer on every detected sample of speech
          if (silenceTimerRef.current) {
            clearTimeout(silenceTimerRef.current);
            silenceTimerRef.current = null;
          }
        } else if (speechDetected && !silenceTimerRef.current) {
          // first silent sample after speech — start countdown
          silenceTimerRef.current = setTimeout(() => {
            stopRecordingRef.current?.();
          }, SILENCE_DURATION_MS);
        }

        // hard cap on utterance length
        if (elapsed > MAX_UTTERANCE_MS) {
          stopRecordingRef.current?.();
          return;
        }

        if (analyzerRef.current && !cancelledRef.current) {
          requestAnimationFrame(tick);
        }
      };
      requestAnimationFrame(tick);
    } catch (error) {
      console.error("Voice mode mic error:", error);
      setState(STATES.ERROR);
      setStatusText(`Mic error: ${error.message?.slice(0, 80) || "unknown"}`);
      toast.error("Microphone access denied");
    }
  }, [onClose]);

  // ---------------- Stop recording + transcribe + send -----------------------

  const stopRecording = useCallback(async () => {
    if (silenceTimerRef.current) { clearTimeout(silenceTimerRef.current); silenceTimerRef.current = null; }
    if (idleTimerRef.current) { clearTimeout(idleTimerRef.current); idleTimerRef.current = null; }

    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === "inactive") return;

    const elapsed = Date.now() - utteranceStartRef.current;
    if (elapsed < MIN_UTTERANCE_MS) {
      // too short — restart listening
      try { recorder.stop(); } catch { /* no-op */ }
      audioStreamRef.current?.getTracks().forEach((t) => t.stop());
      audioContextRef.current?.close();
      audioStreamRef.current = null;
      audioContextRef.current = null;
      analyzerRef.current = null;
      setTimeout(() => { if (!cancelledRef.current) startListening(); }, 200);
      return;
    }

    recorder.onstop = async () => {
      // Tear down audio graph before async network work
      audioStreamRef.current?.getTracks().forEach((t) => t.stop());
      audioContextRef.current?.close().catch(() => {});
      audioStreamRef.current = null;
      audioContextRef.current = null;
      analyzerRef.current = null;

      if (cancelledRef.current) return;
      const blob = new Blob(chunksRef.current, { type: "audio/webm" });
      chunksRef.current = [];

      setState(STATES.TRANSCRIBING);
      setStatusText("Transcribing…");
      try {
        const result = await transcribeAudio(blob);
        const text = (result?.text || "").trim();
        if (!text) {
          setStatusText("Couldn't catch that — try again");
          setTimeout(() => { if (!cancelledRef.current) startListening(); }, 800);
          return;
        }
        setTranscript(text);
        setState(STATES.THINKING);
        setStatusText(`You: "${text.length > 60 ? text.slice(0, 60) + "…" : text}"`);
        await onSendMessage(text);
      } catch (error) {
        console.error("Voice mode transcribe error:", error);
        setStatusText("Transcribe failed — listening again");
        setTimeout(() => { if (!cancelledRef.current) startListening(); }, 1200);
      }
    };
    try { recorder.stop(); } catch { /* no-op */ }
  }, [transcribeAudio, onSendMessage, startListening]);

  // expose for the analyzer loop without re-creating it on every render
  useEffect(() => { stopRecordingRef.current = stopRecording; }, [stopRecording]);

  // ---------------- Speak Aria's reply when it arrives ----------------------

  useEffect(() => {
    if (state !== STATES.THINKING) return;
    if (!lastAssistantMessage) return;
    if (lastAssistantMessage.id === lastSpokenIdRef.current) return;
    if (busy) return;

    lastSpokenIdRef.current = lastAssistantMessage.id;
    setState(STATES.SPEAKING);
    setStatusText("Aria is speaking…");

    speakText(lastAssistantMessage.content).then(() => {
      if (cancelledRef.current) return;
      // Brief pause so Aria's tail-end isn't picked up by the mic
      setTimeout(() => { if (!cancelledRef.current) startListening(); }, 400);
    }).catch((error) => {
      console.error("Voice mode TTS error:", error);
      setStatusText("Speech failed — listening again");
      setTimeout(() => { if (!cancelledRef.current) startListening(); }, 800);
    });
  }, [state, lastAssistantMessage, busy, speakText, startListening]);

  // ---------------- Lifecycle: start on mount, cleanup on unmount -----------

  useEffect(() => {
    cancelledRef.current = false;
    const start = setTimeout(() => { if (!cancelledRef.current) startListening(); }, 600);
    const onKey = (event) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => {
      cancelledRef.current = true;
      clearTimeout(start);
      window.removeEventListener("keydown", onKey);
      try { mediaRecorderRef.current?.stop(); } catch { /* no-op */ }
      audioStreamRef.current?.getTracks().forEach((t) => t.stop());
      audioContextRef.current?.close().catch(() => {});
      try { window.speechSynthesis.cancel(); } catch { /* no-op */ }
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ---------------- UI ------------------------------------------------------

  const ringClass = `vfm-ring vfm-ring-${state}`;

  return (
    <div className="vfm-overlay" data-testid="caos-voice-first-overlay" role="dialog" aria-label="Voice-first mode">
      <button
        className="vfm-close"
        data-testid="caos-voice-first-close"
        onClick={onClose}
        type="button"
        aria-label="Exit voice mode"
        title="Exit voice mode (Esc)"
      ><X size={22} /></button>

      <div className={ringClass} aria-hidden="true">
        <div className="vfm-ring-inner">
          {state === STATES.LISTENING && <Mic size={64} />}
          {state === STATES.TRANSCRIBING && <Loader size={64} className="vfm-spin" />}
          {state === STATES.THINKING && <Loader size={64} className="vfm-spin" />}
          {state === STATES.SPEAKING && <Volume2 size={64} />}
          {state === STATES.IDLE && <Mic size={64} />}
          {state === STATES.ERROR && <X size={64} />}
        </div>
      </div>

      <div className="vfm-status" aria-live="polite" data-testid="caos-voice-first-status">
        {statusText}
      </div>

      {transcript ? (
        <div className="vfm-transcript" data-testid="caos-voice-first-transcript">
          <span className="vfm-transcript-label">You said</span>
          <span>{transcript}</span>
        </div>
      ) : null}

      <button
        className="vfm-exit-btn"
        data-testid="caos-voice-first-exit-button"
        onClick={onClose}
        type="button"
      >Exit voice mode (Esc)</button>
    </div>
  );
};

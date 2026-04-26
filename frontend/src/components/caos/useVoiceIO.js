import { useCallback, useRef } from "react";
import axios from "axios";

import { API } from "@/config/apiBase";

/**
 * Voice I/O hook — Whisper transcription (full + chunk) and browser TTS.
 * Lives outside useCaosShell to keep the shell orchestrator under 400 lines.
 */
export const useVoiceIO = ({ userEmail, voiceSettings }) => {
  // Track active utterance globally so stop button can cancel properly
  const activeUtteranceRef = useRef(null);

  const transcribeAudio = useCallback(async (blob, filename = "caos-voice-note.webm") => {
    const form = new FormData();
    form.append("user_email", userEmail);
    form.append("model", voiceSettings.stt_primary_model);
    form.append("fallback_model", voiceSettings.stt_fallback_model);
    form.append("language", voiceSettings.stt_language);
    form.append("file", new File([blob], filename, { type: blob.type || "audio/webm" }));
    const response = await axios.post(`${API}/caos/voice/transcribe`, form, { withCredentials: true });
    return response.data;
  }, [userEmail, voiceSettings.stt_fallback_model, voiceSettings.stt_language, voiceSettings.stt_primary_model]);

  const transcribeAudioChunk = useCallback(async (blob, prompt = "", filename = "caos-voice-chunk.webm") => {
    const form = new FormData();
    form.append("user_email", userEmail);
    form.append("model", voiceSettings.stt_primary_model);
    form.append("fallback_model", voiceSettings.stt_fallback_model);
    form.append("language", voiceSettings.stt_language);
    if (prompt.trim()) form.append("prompt", prompt.slice(-180));
    form.append("file", new File([blob], filename, { type: blob.type || "audio/webm" }));
    const response = await axios.post(`${API}/caos/voice/transcribe`, form, { withCredentials: true });
    return response.data;
  }, [userEmail, voiceSettings.stt_fallback_model, voiceSettings.stt_language, voiceSettings.stt_primary_model]);

  const speakText = useCallback(async (text, overrides = {}) => {
    // Primary: Browser's native speechSynthesis for instant playback.
    // Cancel any existing speech first (fixes stop button buffering issue)
    if (activeUtteranceRef.current) {
      window.speechSynthesis.cancel();
      activeUtteranceRef.current = null;
    }
    
    if (typeof window === "undefined" || !window.speechSynthesis) {
      throw new Error("Your browser doesn't support speech synthesis");
    }
    let voices = window.speechSynthesis.getVoices();
    if (!voices || voices.length === 0) {
      await new Promise((resolve) => {
        const timer = setTimeout(resolve, 500);
        window.speechSynthesis.onvoiceschanged = () => { clearTimeout(timer); resolve(); };
      });
      voices = window.speechSynthesis.getVoices();
    }
    if (!voices || voices.length === 0) {
      throw new Error("No TTS voices on this system. On Ubuntu: sudo apt install speech-dispatcher");
    }
    // Strip markdown formatting so it doesn't read "asterisk asterisk" etc.
    const cleanText = text
      .replace(/```[\s\S]*?```/g, " code block ") // code blocks
      .replace(/`([^`]+)`/g, "$1") // inline code
      .replace(/\*\*([^*]+)\*\*/g, "$1") // bold
      .replace(/\*([^*]+)\*/g, "$1") // italic
      .replace(/__([^_]+)__/g, "$1") // bold underscore
      .replace(/_([^_]+)_/g, "$1") // italic underscore
      .replace(/~~([^~]+)~~/g, "$1") // strikethrough
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1") // links
      .replace(/^#{1,6}\s+/gm, "") // headers
      .replace(/^\s*[-*+]\s+/gm, "") // list bullets
      .replace(/^\s*\d+\.\s+/gm, "") // numbered lists
      .replace(/\n{3,}/g, "\n\n") // excessive newlines
      .trim();
    
    const utter = new SpeechSynthesisUtterance(cleanText);
    utter.rate = overrides.speed || voiceSettings.tts_speed || 1.0;
    
    // Cleanup when speech ends naturally
    utter.onend = () => { activeUtteranceRef.current = null; };
    utter.onerror = () => { activeUtteranceRef.current = null; };
    
    activeUtteranceRef.current = utter;
    window.speechSynthesis.speak(utter);
    return utter;
  }, [voiceSettings.tts_speed]);

  // API-driven TTS via OpenAI gpt-4o-mini-tts. Used by the message-bubble
  // Read button so it works on every OS (Linux without speech-dispatcher,
  // Windows, mac) — quality is studio-grade vs. robotic system voice.
  // Costs ~$0.015/1K chars, so each click on a typical reply is ~$0.001.
  const apiAudioRef = useRef(null);
  const speakTextApi = useCallback(async (text, overrides = {}) => {
    // Stop browser-native speech if it's running so the two paths don't overlap.
    try { window.speechSynthesis?.cancel(); } catch { /* no-op */ }
    activeUtteranceRef.current = null;
    // Stop any prior API audio playback (toggle-off behavior).
    if (apiAudioRef.current) {
      try { apiAudioRef.current.pause(); apiAudioRef.current.src = ""; } catch { /* no-op */ }
      apiAudioRef.current = null;
    }
    const cleanText = (text || "")
      .replace(/```[\s\S]*?```/g, " code block ")
      .replace(/`([^`]+)`/g, "$1")
      .replace(/\*\*([^*]+)\*\*/g, "$1")
      .replace(/\*([^*]+)\*/g, "$1")
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
      .replace(/^#{1,6}\s+/gm, "")
      .replace(/^\s*[-*+]\s+/gm, "")
      .replace(/^\s*\d+\.\s+/gm, "")
      .trim()
      .slice(0, 4000);  // backend hard-cap is 4096; keep margin
    if (!cleanText) return null;
    const resp = await axios.post(
      `${API}/caos/voice/tts`,
      {
        text: cleanText,
        voice: overrides.voice || voiceSettings.tts_voice || "nova",
        speed: overrides.speed || voiceSettings.tts_speed || 1.0,
        model: overrides.model || voiceSettings.tts_model || "gpt-4o-mini-tts",
      },
      { withCredentials: true }
    );
    const b64 = resp.data?.audio_base64 || resp.data?.audio_b64 || resp.data?.audio;
    if (!b64) {
      throw new Error(resp.data?.error || "TTS server returned no audio");
    }
    // Decode base64 → Blob → object URL → play.
    const binary = atob(b64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    const blob = new Blob([bytes], { type: resp.data?.content_type || resp.data?.mime_type || "audio/mpeg" });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.onended = () => { URL.revokeObjectURL(url); apiAudioRef.current = null; };
    audio.onerror = () => { URL.revokeObjectURL(url); apiAudioRef.current = null; };
    apiAudioRef.current = audio;
    await audio.play();
    return audio;
  }, [voiceSettings.tts_model, voiceSettings.tts_speed, voiceSettings.tts_voice]);

  return { transcribeAudio, transcribeAudioChunk, speakText, speakTextApi };
};

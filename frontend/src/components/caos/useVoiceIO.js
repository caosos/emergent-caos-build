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
    const response = await axios.post(`${API}/caos/voice/transcribe`, form);
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
    const response = await axios.post(`${API}/caos/voice/transcribe`, form);
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

  return { transcribeAudio, transcribeAudioChunk, speakText };
};

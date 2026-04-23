import { useCallback } from "react";
import axios from "axios";

import { API } from "@/config/apiBase";

/**
 * Voice I/O hook — Whisper transcription (full + chunk) and OpenAI TTS with
 * browser speechSynthesis fallback. Lives outside useCaosShell to keep the
 * shell orchestrator under the 400-line GOV v1.2 cap.
 */
export const useVoiceIO = ({ userEmail, voiceSettings }) => {
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
    // This avoids the 1-2 minute wait to download WAV files from OpenAI TTS API.
    // On Linux/Chrome without speech-dispatcher, voices may be empty — we wait
    // briefly for voiceschanged and then throw a specific, actionable error.
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
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.rate = overrides.speed || voiceSettings.tts_speed || 1.0;
    window.speechSynthesis.speak(utter);
    return utter;
  }, [voiceSettings.tts_speed]);

  return { transcribeAudio, transcribeAudioChunk, speakText };
};

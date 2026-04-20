import { useCallback } from "react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

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
    // Primary: OpenAI TTS via backend proxy. Fallback: browser speechSynthesis.
    // Backend TTS currently returns 500 at the Emergent proxy layer — fallback
    // keeps Read Aloud functional while the support ticket is open.
    try {
      const response = await axios.post(`${API}/caos/voice/tts`, {
        text,
        voice: overrides.voice || voiceSettings.tts_voice,
        model: overrides.model || voiceSettings.tts_model,
        speed: overrides.speed || voiceSettings.tts_speed,
      });
      const audio = new Audio(`data:${response.data.content_type};base64,${response.data.audio_base64}`);
      await audio.play();
      return audio;
    } catch (error) {
      if (typeof window !== "undefined" && window.speechSynthesis) {
        window.speechSynthesis.cancel();
        const utter = new SpeechSynthesisUtterance(text);
        utter.rate = overrides.speed || voiceSettings.tts_speed || 1.0;
        window.speechSynthesis.speak(utter);
        return utter;
      }
      throw error;
    }
  }, [voiceSettings.tts_model, voiceSettings.tts_speed, voiceSettings.tts_voice]);

  return { transcribeAudio, transcribeAudioChunk, speakText };
};

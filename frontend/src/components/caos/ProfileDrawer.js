import { UserRound, X } from "lucide-react";


const STT_MODELS = [
  { value: "gpt-4o-transcribe", label: "GPT-4o Transcribe" },
  { value: "whisper-1", label: "Whisper-1" },
];
const TTS_VOICES = ["nova", "alloy", "verse"];


export const ProfileDrawer = ({ isOpen, memoryCount, onClose, profile, runtimeSettings, sessionsCount, updateVoiceSettings, userEmail, voiceSettings }) => {
  if (!isOpen) return null;

  return (
    <div className="drawer-overlay" data-testid="caos-profile-drawer-overlay">
      <aside className="drawer-shell" data-testid="caos-profile-drawer">
        <div className="drawer-header">
          <div className="context-card-heading">
            <UserRound size={16} />
            <h2 data-testid="caos-profile-drawer-heading">Profile</h2>
          </div>
          <button className="drawer-close-button" data-testid="caos-profile-drawer-close-button" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <div className="drawer-card" data-testid="caos-profile-user-card">
          <span>Email</span>
          <strong data-testid="caos-profile-email-value">{profile?.user_email || userEmail}</strong>
        </div>
        <div className="drawer-card" data-testid="caos-profile-environment-card">
          <span>Environment</span>
          <strong data-testid="caos-profile-environment-value">{profile?.environment_name || "CAOS"}</strong>
        </div>
        <div className="drawer-card" data-testid="caos-profile-assistant-card">
          <span>Companion intelligence</span>
          <strong data-testid="caos-profile-assistant-value">{profile?.assistant_name || "Aria"}</strong>
        </div>
        <div className="drawer-card" data-testid="caos-profile-session-count-card">
          <span>Saved threads</span>
          <strong data-testid="caos-profile-session-count-value">{sessionsCount}</strong>
        </div>
        <div className="drawer-card" data-testid="caos-profile-memory-count-card">
          <span>Permanent memories</span>
          <strong data-testid="caos-profile-memory-count-value">{memoryCount}</strong>
        </div>
        <div className="drawer-card" data-testid="caos-profile-runtime-card">
          <span>Inference routing</span>
          <strong data-testid="caos-profile-runtime-value">{runtimeSettings?.key_source || "hybrid"}</strong>
        </div>
        <div className="drawer-card" data-testid="caos-profile-provider-card">
          <span>Active engine</span>
          <strong data-testid="caos-profile-provider-value">{runtimeSettings?.default_provider || "openai"} · {runtimeSettings?.default_model || "gpt-5.2"}</strong>
        </div>

        <div className="drawer-section" data-testid="caos-profile-voice-settings-section">
          <h3 data-testid="caos-profile-voice-settings-heading">Voice settings</h3>
          <div className="drawer-card" data-testid="caos-profile-stt-card">
            <span>Primary speech-to-text</span>
            <strong data-testid="caos-profile-stt-primary-value">{voiceSettings?.stt_primary_model || "gpt-4o-transcribe"}</strong>
            <div className="surface-button-row" data-testid="caos-profile-stt-model-row">
              {STT_MODELS.map((model) => (
                <button
                  className={`message-action-button ${voiceSettings?.stt_primary_model === model.value ? "drawer-option-active" : ""}`}
                  data-testid={`caos-profile-stt-model-${model.value}`}
                  key={model.value}
                  onClick={() => updateVoiceSettings({ stt_primary_model: model.value })}
                  type="button"
                >
                  {model.label}
                </button>
              ))}
            </div>
          </div>
          <div className="drawer-card" data-testid="caos-profile-stt-fallback-card">
            <span>Fallback speech-to-text</span>
            <strong data-testid="caos-profile-stt-fallback-value">{voiceSettings?.stt_fallback_model || "whisper-1"}</strong>
          </div>
          <div className="drawer-card" data-testid="caos-profile-tts-card">
            <span>Read-aloud voice</span>
            <strong data-testid="caos-profile-tts-voice-value">{voiceSettings?.tts_voice || "nova"}</strong>
            <div className="surface-button-row" data-testid="caos-profile-tts-voice-row">
              {TTS_VOICES.map((voice) => (
                <button
                  className={`message-action-button ${voiceSettings?.tts_voice === voice ? "drawer-option-active" : ""}`}
                  data-testid={`caos-profile-tts-voice-${voice}`}
                  key={voice}
                  onClick={() => updateVoiceSettings({ tts_voice: voice })}
                  type="button"
                >
                  {voice}
                </button>
              ))}
            </div>
          </div>
          <div className="drawer-card" data-testid="caos-profile-voice-language-card">
            <span>Input language</span>
            <strong data-testid="caos-profile-voice-language-value">{voiceSettings?.stt_language || "en"}</strong>
          </div>
        </div>

        <div className="drawer-list" data-testid="caos-profile-memory-list">
          {(profile?.structured_memory || []).slice(0, 8).map((memory) => (
            <div className="drawer-list-item" data-testid={`caos-profile-memory-${memory.id}`} key={memory.id}>
              {memory.content}
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
};
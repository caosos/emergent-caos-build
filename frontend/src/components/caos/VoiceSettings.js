import { useEffect, useRef, useState } from "react";
import { Check, Play, Volume2, X } from "lucide-react";
import { toast } from "sonner";

import { Slider } from "@/components/ui/slider";

const OPENAI_VOICES = [
  { id: "alloy", name: "Alloy", description: "Neutral, balanced" },
  { id: "echo", name: "Echo", description: "Male, clear" },
  { id: "fable", name: "Fable", description: "British, expressive" },
  { id: "onyx", name: "Onyx", description: "Male, deep" },
  { id: "nova", name: "Nova", description: "Female, warm (Default)" },
  { id: "shimmer", name: "Shimmer", description: "Female, soft" },
];

export const VoiceSettings = ({ isOpen, onClose, voiceSettings, onSave, onSpeak }) => {
  const [selected, setSelected] = useState(voiceSettings?.tts_voice || "nova");
  const [speed, setSpeed] = useState(voiceSettings?.tts_speed || 1.0);
  const [testing, setTesting] = useState(null);
  const shellRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return undefined;
    const handler = (event) => {
      if (shellRef.current && !shellRef.current.contains(event.target)) onClose();
    };
    const esc = (event) => { if (event.key === "Escape") onClose(); };
    document.addEventListener("mousedown", handler);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", handler);
      document.removeEventListener("keydown", esc);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleTest = async (voiceId) => {
    if (testing === voiceId) { setTesting(null); return; }
    setTesting(voiceId);
    try {
      await onSpeak("Hey, I'm Aria. How does this voice sound?", { voice: voiceId, speed });
    } catch (error) {
      toast.error(`Preview unavailable: ${(error?.message || "unknown").slice(0, 60)}`);
    } finally {
      setTesting(null);
    }
  };

  const handleSave = async () => {
    try {
      await onSave({ tts_voice: selected, tts_speed: speed });
      toast.success("Voice settings saved");
      onClose();
    } catch (error) {
      toast.error(`Save failed: ${(error?.message || "unknown").slice(0, 60)}`);
    }
  };

  return (
    <div className="voice-settings-overlay" data-testid="caos-voice-settings-overlay">
      <div className="voice-settings-shell" data-testid="caos-voice-settings" ref={shellRef}>
        <div className="voice-settings-header">
          <div className="voice-settings-heading">
            <Volume2 size={16} />
            <h2 data-testid="caos-voice-settings-title">Voice & Speech</h2>
          </div>
          <button className="drawer-close-button" data-testid="caos-voice-settings-close" onClick={onClose} type="button">
            <X size={16} />
          </button>
        </div>

        <div className="voice-settings-body" data-testid="caos-voice-settings-body">
          <div className="voice-settings-section" data-testid="caos-voice-settings-voices-section">
            <h3>OpenAI voice</h3>
            <p className="voice-settings-hint">Pick a voice. Tap ▶ to preview. Changes save when you click Save.</p>
            <div className="voice-settings-grid" data-testid="caos-voice-settings-grid">
              {OPENAI_VOICES.map((voice) => {
                const isActive = selected === voice.id;
                const isTesting = testing === voice.id;
                return (
                  <button
                    className={`voice-settings-card ${isActive ? "voice-settings-card-active" : ""}`}
                    data-testid={`caos-voice-card-${voice.id}`}
                    key={voice.id}
                    onClick={() => setSelected(voice.id)}
                    type="button"
                  >
                    <div className="voice-settings-card-main">
                      <strong data-testid={`caos-voice-card-name-${voice.id}`}>{voice.name}</strong>
                      <span data-testid={`caos-voice-card-desc-${voice.id}`}>{voice.description}</span>
                    </div>
                    <div className="voice-settings-card-actions">
                      <button
                        aria-label={`Preview ${voice.name}`}
                        className="voice-settings-test"
                        data-testid={`caos-voice-card-preview-${voice.id}`}
                        onClick={(event) => { event.stopPropagation(); handleTest(voice.id); }}
                        type="button"
                      >
                        <Play size={12} />{isTesting ? "Stop" : "Test"}
                      </button>
                      {isActive ? <Check size={14} className="voice-settings-active-check" /> : null}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="voice-settings-section" data-testid="caos-voice-settings-speed-section">
            <h3>Speed</h3>
            <div className="voice-settings-speed-row">
              <span data-testid="caos-voice-speed-label">{speed.toFixed(2)}×</span>
              <Slider
                data-testid="caos-voice-speed-slider"
                max={2.0}
                min={0.5}
                onValueChange={([value]) => setSpeed(Number(value) || 1.0)}
                step={0.05}
                value={[speed]}
              />
            </div>
          </div>
        </div>

        <div className="voice-settings-footer" data-testid="caos-voice-settings-footer">
          <button className="voice-settings-cancel" data-testid="caos-voice-settings-cancel" onClick={onClose} type="button">Cancel</button>
          <button className="voice-settings-save" data-testid="caos-voice-settings-save" onClick={handleSave} type="button">Save</button>
        </div>
      </div>
    </div>
  );
};

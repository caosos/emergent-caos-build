/**
 * NameYourAssistant
 * -----------------
 * First-run onboarding modal shown ONCE after signup. Asks the user what they
 * want their AI assistant to be called. 6 preset buttons + a custom input +
 * "Skip (call her Aria)" escape hatch. POSTs to /caos/profile/upsert, flips
 * localStorage flag, then hands off to the WelcomeTour.
 */
import { useState } from "react";
import axios from "axios";
import { Sparkles } from "lucide-react";
import { toast } from "sonner";

import { API } from "@/config/apiBase";

const PRESETS = ["Aria", "Nova", "Axis", "Luna", "Echo", "Kai", "Sage"];

export const NameYourAssistant = ({ isOpen, userEmail, onChosen }) => {
  const [selected, setSelected] = useState("Aria");
  const [custom, setCustom] = useState("");
  const [saving, setSaving] = useState(false);

  if (!isOpen) return null;

  const finalName = (custom || selected).trim().slice(0, 30) || "Aria";

  const commit = async (name) => {
    setSaving(true);
    try {
      await axios.post(`${API}/caos/profile/upsert`, {
        user_email: userEmail,
        assistant_name: name,
      }, { withCredentials: true });
      try { localStorage.setItem("caos_assistant_named", "true"); } catch { /* noop */ }
      toast.success(`Say hi to ${name} 👋`, { duration: 2200 });
      onChosen?.(name);
    } catch (error) {
      toast.error(`Couldn't save — we'll call her Aria for now`);
      try { localStorage.setItem("caos_assistant_named", "true"); } catch { /* noop */ }
      onChosen?.("Aria");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="name-assistant-backdrop" data-testid="caos-name-assistant-backdrop">
      <div className="name-assistant-modal" data-testid="caos-name-assistant-modal">
        <div className="name-assistant-icon"><Sparkles size={22} /></div>
        <h2 data-testid="caos-name-assistant-title">Name your AI</h2>
        <p>She's yours. What should we call her?</p>
        <div className="name-assistant-presets" data-testid="caos-name-assistant-presets">
          {PRESETS.map((preset) => (
            <button
              key={preset}
              type="button"
              className={`name-assistant-preset ${selected === preset && !custom ? "name-assistant-preset-active" : ""}`}
              data-testid={`caos-name-assistant-preset-${preset.toLowerCase()}`}
              onClick={() => { setSelected(preset); setCustom(""); }}
            >{preset}</button>
          ))}
        </div>
        <div className="name-assistant-custom-row">
          <span>or something else:</span>
          <input
            type="text"
            placeholder="e.g. Juno, Atlas, Iris…"
            maxLength={30}
            value={custom}
            onChange={(event) => setCustom(event.target.value)}
            onKeyDown={(event) => { if (event.key === "Enter") { event.preventDefault(); commit(finalName); } }}
            data-testid="caos-name-assistant-custom-input"
          />
        </div>
        <div className="name-assistant-actions">
          <button
            type="button"
            className="name-assistant-skip"
            data-testid="caos-name-assistant-skip"
            disabled={saving}
            onClick={() => commit("Aria")}
          >Skip (call her Aria)</button>
          <button
            type="button"
            className="name-assistant-confirm"
            data-testid="caos-name-assistant-confirm"
            disabled={saving}
            onClick={() => commit(finalName)}
          >{saving ? "Saving…" : `Meet ${finalName}`}</button>
        </div>
      </div>
    </div>
  );
};

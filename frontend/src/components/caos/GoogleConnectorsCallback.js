import { useEffect, useState } from "react";
import axios from "axios";
import { toast } from "sonner";

import { API } from "@/config/apiBase";

/**
 * GoogleConnectorsCallback — frontend route that the OAuth popup lands on.
 *
 * The popup opens at this URL with `?code=...&state=...` (or `?error=...`)
 * after Google's consent screen. We POST those values to the backend, then
 * post a message to the parent window and close ourselves.
 *
 * REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS,
 * THIS BREAKS THE AUTH.
 */
export const GoogleConnectorsCallback = () => {
  const [phase, setPhase] = useState("processing");
  const [detail, setDetail] = useState("Finalizing Google connection…");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const state = params.get("state");
    const errorParam = params.get("error");

    const post = (payload) => {
      try {
        if (window.opener && !window.opener.closed) {
          window.opener.postMessage({ type: "caos_google_oauth", ...payload }, window.location.origin);
        }
      } catch (_) { /* ignore */ }
    };

    const finish = () => {
      setTimeout(() => {
        try { window.close(); } catch (_) { /* ignore */ }
      }, 600);
    };

    if (errorParam) {
      setPhase("error");
      setDetail(errorParam);
      post({ error: errorParam });
      finish();
      return;
    }
    if (!code || !state) {
      setPhase("error");
      setDetail("Missing code or state from Google. Close this window and try again.");
      post({ error: "missing code/state" });
      finish();
      return;
    }

    (async () => {
      try {
        // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS,
        // THIS BREAKS THE AUTH. We send the SAME redirect_uri the backend
        // generated at /start time so Google's exchange validation matches.
        const redirectUri = `${window.location.origin}/auth/google-connectors-callback`;
        const resp = await axios.post(
          `${API}/connectors/google/callback`,
          { code, state, redirect_uri: redirectUri },
          { withCredentials: true },
        );
        if (!resp.data?.ok) throw new Error(resp.data?.error || "callback failed");
        setPhase("ok");
        setDetail(`Connected as ${resp.data.email || "your Google account"}.`);
        post({ payload: resp.data });
      } catch (err) {
        const msg = err?.response?.data?.detail || err?.message || "Connection failed";
        setPhase("error");
        setDetail(msg);
        post({ error: msg });
        try { toast.error(msg); } catch (_) { /* ignore */ }
      } finally {
        finish();
      }
    })();
  }, []);

  return (
    <div
      data-testid="caos-google-connectors-callback"
      style={{
        position: "fixed", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
        background: "#070710", color: "#e2e8f0", fontFamily: "ui-sans-serif, system-ui, sans-serif",
      }}
    >
      <div style={{ maxWidth: 420, padding: "28px 24px", borderRadius: 14, border: "1px solid rgba(167,139,250,0.35)", background: "rgba(15,15,28,0.85)", textAlign: "center" }}>
        <h1 style={{ fontSize: 18, margin: 0, color: "#f5f3ff" }}>
          {phase === "ok" ? "Google connected" : phase === "error" ? "Connection failed" : "Connecting Google…"}
        </h1>
        <p style={{ marginTop: 12, color: "rgba(226,232,240,0.75)", fontSize: 13.5, lineHeight: 1.55 }}>
          {detail}
        </p>
        <p style={{ marginTop: 16, fontSize: 11.5, color: "rgba(167,139,250,0.7)" }}>This window will close automatically.</p>
      </div>
    </div>
  );
};

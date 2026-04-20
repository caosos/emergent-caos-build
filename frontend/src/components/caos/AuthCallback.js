import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * OAuth callback handler.
 *
 * When the user returns from Google auth they land at `/#session_id=xxx`.
 * This component detects the session_id synchronously, POSTs it to the backend
 * `/auth/process-session` endpoint (which exchanges it for a 7-day cookie),
 * then redirects to the dashboard.
 *
 * REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
 */
export const AuthCallback = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const processed = useRef(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;
    const match = location.hash.match(/session_id=([^&]+)/);
    const sessionId = match ? decodeURIComponent(match[1]) : null;
    if (!sessionId) {
      setError("Missing session_id in URL fragment");
      return;
    }
    axios.post(`${API}/auth/process-session`, { session_id: sessionId }, { withCredentials: true })
      .then((response) => {
        navigate("/", { replace: true, state: { user: response.data } });
      })
      .catch((issue) => {
        setError(issue?.response?.data?.detail || issue?.message || "Auth failed");
      });
  }, [location, navigate]);

  return (
    <div style={{ padding: 40, color: "#ccc", textAlign: "center" }} data-testid="caos-auth-callback">
      {error ? (
        <>
          <h2 style={{ color: "#fca5a5" }}>Sign-in failed</h2>
          <p>{error}</p>
          <a href="/" style={{ color: "#a78bfa" }}>Back to login</a>
        </>
      ) : (
        <h2>Completing sign-in…</h2>
      )}
    </div>
  );
};

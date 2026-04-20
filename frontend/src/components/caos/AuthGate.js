import { useEffect, useState } from "react";
import axios from "axios";
import { Loader2 } from "lucide-react";

import { CaosShell } from "@/components/caos/CaosShell";
import { LoginScreen } from "@/components/caos/LoginScreen";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * Three-state auth gate: null → checking, user → authenticated, false → not.
 *
 * If the URL fragment contains `session_id=` we skip the /auth/me probe and
 * let AuthCallback handle the exchange (avoids a 401 race condition).
 */
export const AuthGate = () => {
  const [user, setUser] = useState(null);

  useEffect(() => {
    let cancelled = false;
    axios.get(`${API}/auth/me`, { withCredentials: true })
      .then((response) => { if (!cancelled) setUser(response.data); })
      .catch(() => { if (!cancelled) setUser(false); });
    return () => { cancelled = true; };
  }, []);

  if (user === null) {
    return (
      <div style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center", color: "#a78bfa" }}
           data-testid="caos-auth-loading">
        <Loader2 className="spin" size={20} style={{ marginRight: 10 }} />
        <span>Verifying session…</span>
      </div>
    );
  }
  if (!user) return <LoginScreen />;
  return <CaosShell authenticatedUser={user} />;
};

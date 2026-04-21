import { useEffect, useState } from "react";
import axios from "axios";
import { Loader2 } from "lucide-react";

import { CaosShell } from "@/components/caos/CaosShell";
import { LoginScreen } from "@/components/caos/LoginScreen";
import { WelcomeTour } from "@/components/caos/WelcomeTour";
import { API } from "@/config/apiBase";

/**
 * Auth gate states:
 *   null       → probing /auth/me
 *   user obj   → authenticated → render CaosShell
 *   false      → unauthenticated → render LoginScreen (pre-login Welcome)
 *   "guest"    → continue-as-guest path → render CaosShell with anon identity
 *
 * Also manages the 5-step WelcomeTour on first run (persisted via localStorage).
 */
export const AuthGate = () => {
  const [user, setUser] = useState(null);
  const [showTour, setShowTour] = useState(false);

  useEffect(() => {
    let cancelled = false;
    axios.get(`${API}/auth/me`, { withCredentials: true })
      .then((response) => {
        if (cancelled) return;
        try { localStorage.removeItem("caos_guest_mode"); } catch {}
        setUser(response.data);
      })
      .catch(() => { if (!cancelled) setUser(false); });
    return () => { cancelled = true; };
  }, []);

  // First-run detection: if authenticated and tour never completed, auto-open.
  useEffect(() => {
    if (!user || user === "guest") return;
    try {
      const done = localStorage.getItem("caos_tour_completed") === "true";
      if (!done) setShowTour(true);
    } catch {}
  }, [user]);

  const handleTakeTour = () => {
    // Guest tour path — show tour over the pre-login screen itself.
    setShowTour(true);
  };

  const handleContinueAsGuest = () => {
    try { localStorage.setItem("caos_guest_mode", "true"); } catch {}
    setUser("guest");
  };

  if (user === null) {
    return (
      <div
        style={{ display: "flex", height: "100vh", alignItems: "center", justifyContent: "center", color: "#a78bfa" }}
        data-testid="caos-auth-loading"
      >
        <Loader2 className="spin" size={20} style={{ marginRight: 10 }} />
        <span>Verifying session…</span>
      </div>
    );
  }

  if (!user) {
    return (
      <>
        <LoginScreen
          onContinueAsGuest={handleContinueAsGuest}
          onTakeTour={handleTakeTour}
        />
        <WelcomeTour
          isOpen={showTour}
          onClose={() => setShowTour(false)}
          onComplete={() => setShowTour(false)}
        />
      </>
    );
  }

  const shellUser = user === "guest"
    ? { email: "guest@caos.local", name: "Guest", picture: "", role: "guest", is_admin: false }
    : user;

  return (
    <>
      <CaosShell authenticatedUser={shellUser} />
      <WelcomeTour
        isOpen={showTour}
        onClose={() => setShowTour(false)}
        onComplete={() => setShowTour(false)}
      />
    </>
  );
};

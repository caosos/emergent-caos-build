import { useEffect, useState } from "react";
import axios from "axios";
import { Loader2 } from "lucide-react";

import { CaosShell } from "@/components/caos/CaosShell";
import { LoginScreen } from "@/components/caos/LoginScreen";
import { NameYourAssistant } from "@/components/caos/NameYourAssistant";
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
  const [showNamePicker, setShowNamePicker] = useState(false);

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

  // First-run detection: on authenticated users, show the name-your-assistant
  // modal ONCE before the welcome tour, so every user gets a personal moment
  // of agency at second #1. Skip for guests.
  useEffect(() => {
    if (!user || user === "guest") return;
    let cancelled = false;
    const syncOnboarding = async () => {
      try {
        const response = await axios.get(`${API}/caos/profile/${encodeURIComponent(user.email)}`, { withCredentials: true });
        if (cancelled) return;
        const hasAssistantName = Boolean(response.data?.assistant_name?.trim());
        const tourDone = localStorage.getItem("caos_tour_completed") === "true";
        if (hasAssistantName) {
          try { localStorage.setItem("caos_assistant_named", "true"); } catch { /* noop */ }
          setShowNamePicker(false);
          if (!tourDone) setShowTour(true);
          return;
        }
        const named = localStorage.getItem("caos_assistant_named") === "true";
        if (!named) setShowNamePicker(true);
        else if (!tourDone) setShowTour(true);
      } catch {
        if (cancelled) return;
        try {
          const named = localStorage.getItem("caos_assistant_named") === "true";
          const tourDone = localStorage.getItem("caos_tour_completed") === "true";
          if (!named) setShowNamePicker(true);
          else if (!tourDone) setShowTour(true);
        } catch { /* noop */ }
      }
    };
    syncOnboarding();
    return () => { cancelled = true; };
  }, [user]);

  const handleNameChosen = () => {
    setShowNamePicker(false);
    try {
      const tourDone = localStorage.getItem("caos_tour_completed") === "true";
      if (!tourDone) setShowTour(true);
    } catch { /* noop */ }
  };

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
      <NameYourAssistant
        isOpen={showNamePicker}
        userEmail={shellUser.email}
        onChosen={handleNameChosen}
      />
      <WelcomeTour
        isOpen={showTour}
        onClose={() => setShowTour(false)}
        onComplete={() => setShowTour(false)}
      />
    </>
  );
};

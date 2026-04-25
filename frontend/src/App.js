import "@/App.css";
import axios from "axios";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";

import { AuthCallback } from "@/components/caos/AuthCallback";
import { AuthGate } from "@/components/caos/AuthGate";
import { CaosErrorBoundary } from "@/components/caos/CaosErrorBoundary";
import { ConstellationLayer } from "@/components/caos/ConstellationLayer";
import { GoogleConnectorsCallback } from "@/components/caos/GoogleConnectorsCallback";

// Every request carries the session_token cookie — auth gate depends on it.
axios.defaults.withCredentials = true;

// Auto-handle expired sessions — if any CAOS API call returns 401 mid-use,
// reload the app so AuthGate re-runs. Skip /auth/me (its 401 is normal during
// the initial probe — AuthGate will flip to LoginScreen on its own).
// Also skip the redirect when running in guest mode (localStorage flag),
// so guests don't get kicked back to the login screen on every protected call.
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const url = error?.config?.url || "";
    const isProtectedApi = url.includes("/api/caos/") || url.includes("/api/auth/logout");
    let isGuest = false;
    try { isGuest = localStorage.getItem("caos_guest_mode") === "true"; } catch {}
    if (status === 401 && isProtectedApi && !isGuest) {
      window.location.replace("/");
    }
    return Promise.reject(error);
  },
);

function App() {
  return (
    <div className="App" data-testid="app-root">
      {/* Constellation renders globally — visible behind login screen AND shell.
          Mounted here so it's not gated on auth. z-index:0 keeps it behind UI. */}
      <ConstellationLayer />
      <CaosErrorBoundary>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<AuthGate />} />
            <Route path="/auth/callback" element={<AuthCallback />} />
            <Route path="/auth/google-connectors-callback" element={<GoogleConnectorsCallback />} />
          </Routes>
        </BrowserRouter>
      </CaosErrorBoundary>
      <Toaster position="bottom-right" theme="dark" richColors closeButton />
    </div>
  );
}

export default App;

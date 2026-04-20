import "@/App.css";
import axios from "axios";
import { BrowserRouter, Route, Routes } from "react-router-dom";
import { Toaster } from "sonner";

import { AuthCallback } from "@/components/caos/AuthCallback";
import { AuthGate } from "@/components/caos/AuthGate";

// Every request carries the session_token cookie — auth gate depends on it.
axios.defaults.withCredentials = true;

// Auto-handle expired sessions — if any CAOS API call returns 401 mid-use,
// reload the app so AuthGate re-runs. Skip /auth/me (its 401 is normal during
// the initial probe — AuthGate will flip to LoginScreen on its own).
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const url = error?.config?.url || "";
    const isProtectedApi = url.includes("/api/caos/") || url.includes("/api/auth/logout");
    if (status === 401 && isProtectedApi) {
      window.location.replace("/");
    }
    return Promise.reject(error);
  },
);

function App() {
  return (
    <div className="App" data-testid="app-root">
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AuthGate />} />
          <Route path="/auth/callback" element={<AuthCallback />} />
        </Routes>
      </BrowserRouter>
      <Toaster position="bottom-right" theme="dark" richColors closeButton />
    </div>
  );
}

export default App;

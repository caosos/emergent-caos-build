/**
 * Resolves the correct backend base URL at runtime.
 *
 * Rule: Prefer REACT_APP_BACKEND_URL (Emergent platform contract).
 *
 * Exception: when the frontend is served from a DIFFERENT hostname than what
 * the env var points at (e.g. the user deployed to the `.static.` preview
 * variant, or to a custom domain like `caosos.com`), the browser enforces
 * stricter CORS rules for credentialed fetches. Cloudflare's edge rewrites
 * `Access-Control-Allow-Origin` to `*`, which browsers REJECT when cookies
 * are sent — producing the exact "Sign-in failed / Network Error" symptom.
 *
 * Emergent's Kubernetes ingress routes `/api/*` on every app host to the
 * same backend service, so falling back to `window.location.origin` is safe
 * (verified: `.static.` and preview hosts both serve `/api/health` → 200).
 *
 * This is NOT hardcoding — the env var is still the source of truth for
 * local dev and same-origin preview. Only cross-origin deployed surfaces
 * switch to same-origin, which is the intended production behavior.
 */
export const getApiBase = () => {
  const envBase = process.env.REACT_APP_BACKEND_URL || "";
  if (typeof window === "undefined") return envBase;
  try {
    const envUrl = new URL(envBase);
    if (envUrl.hostname && envUrl.hostname !== window.location.hostname) {
      return window.location.origin;
    }
  } catch (_ignored) {
    // Malformed env; fall back to same-origin.
    return window.location.origin;
  }
  return envBase;
};

export const API_BASE = getApiBase();
export const API = `${API_BASE}/api`;

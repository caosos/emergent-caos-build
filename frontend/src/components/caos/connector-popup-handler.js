/**
 * OAuth popup helper.
 *
 * Opens a centered popup window pointed at a provider's consent URL,
 * waits for it to post a message back via window.postMessage (the
 * frontend callback route does this), and resolves with the result.
 *
 * The popup MUST live on the SAME origin as the parent so postMessage
 * can be received without origin-check workarounds.
 *
 * REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS,
 * THIS BREAKS THE AUTH. The redirect URI is built from
 * `window.location.origin + "/auth/google-connectors-callback"` per the
 * verified Google OAuth playbook.
 */

const POPUP_W = 540;
const POPUP_H = 720;

export function openOAuthPopup(authUrl, expectedMessageType, timeoutMs = 180000) {
  return new Promise((resolve, reject) => {
    const left = Math.max(0, (window.screen.width - POPUP_W) / 2);
    const top = Math.max(0, (window.screen.height - POPUP_H) / 2);
    const popup = window.open(
      authUrl,
      "caos_oauth_popup",
      `width=${POPUP_W},height=${POPUP_H},left=${left},top=${top}`,
    );
    if (!popup) {
      reject(new Error("Popup blocked. Allow popups for caosos.com and try again."));
      return;
    }

    let settled = false;
    const settle = (result, isError = false) => {
      if (settled) return;
      settled = true;
      window.removeEventListener("message", onMessage);
      clearInterval(closedPoll);
      clearTimeout(timeoutHandle);
      try { if (popup && !popup.closed) popup.close(); } catch (_) { /* noop */ }
      isError ? reject(result) : resolve(result);
    };

    const onMessage = (event) => {
      if (event.origin !== window.location.origin) return;
      const data = event.data || {};
      if (data.type !== expectedMessageType) return;
      if (data.error) settle(new Error(data.error), true);
      else settle(data.payload || {});
    };
    window.addEventListener("message", onMessage);

    // If the user closes the popup manually, abort cleanly.
    const closedPoll = setInterval(() => {
      try {
        if (popup.closed) settle(new Error("Sign-in cancelled."), true);
      } catch (_) { /* cross-origin during the consent screen — ignore */ }
    }, 600);

    const timeoutHandle = setTimeout(
      () => settle(new Error("Sign-in timed out after 3 minutes."), true),
      timeoutMs,
    );
  });
}

export function buildGoogleConnectorsRedirectUri() {
  // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS,
  // THIS BREAKS THE AUTH.
  return `${window.location.origin}/auth/google-connectors-callback`;
}

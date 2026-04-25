import { Component } from "react";

/**
 * CaosErrorBoundary — last-resort fallback for render crashes.
 *
 * Without this, a single component throw (e.g. a missing prop on a deep
 * render) blanks the entire app to white. This boundary catches those,
 * surfaces a dark-themed recovery screen, and offers a one-click reload.
 *
 * Note: error boundaries do NOT catch async errors (network, promise
 * rejections, event handlers). Those are handled by the global axios
 * interceptor and the per-feature catch handlers. This is purely for
 * synchronous render / lifecycle exceptions.
 */
export class CaosErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, info: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    // Log to console — backend error_log isn't reachable from here without
    // the user's session being mounted, and we don't want a fetch storm
    // mid-crash. Errors flagged here are render/lifecycle bugs we should
    // catch in dev anyway.
    // eslint-disable-next-line no-console
    console.error("[CAOS] Render boundary caught:", error, info);
    this.setState({ info });
  }

  handleReload = () => {
    try {
      window.location.reload();
    } catch {
      /* no-op */
    }
  };

  handleClear = () => {
    try {
      // Clear only CAOS-prefixed keys; leave session cookies + auth alone.
      Object.keys(localStorage)
        .filter((key) => key.startsWith("caos_"))
        .forEach((key) => localStorage.removeItem(key));
    } catch {
      /* no-op */
    }
    this.handleReload();
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    const message = this.state.error?.message || "Unknown render error";

    return (
      <div
        data-testid="caos-error-boundary-fallback"
        style={{
          position: "fixed",
          inset: 0,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#070710",
          color: "#e2e8f0",
          fontFamily: "ui-sans-serif, system-ui, -apple-system, sans-serif",
          zIndex: 9999,
        }}
      >
        <div
          style={{
            maxWidth: 520,
            width: "92%",
            padding: "32px 28px",
            borderRadius: 16,
            border: "1px solid rgba(167, 139, 250, 0.35)",
            background: "rgba(15, 15, 28, 0.85)",
            boxShadow: "0 24px 60px rgba(0,0,0,0.55)",
            backdropFilter: "blur(18px)",
          }}
        >
          <h1
            data-testid="caos-error-boundary-title"
            style={{ fontSize: 22, margin: 0, color: "#f5f3ff", letterSpacing: "0.02em" }}
          >
            Something glitched in the shell.
          </h1>
          <p
            data-testid="caos-error-boundary-subtitle"
            style={{ marginTop: 10, color: "rgba(226, 232, 240, 0.7)", fontSize: 14, lineHeight: 1.55 }}
          >
            CAOS hit a render error and stopped cleanly to protect your session.
            Reload to recover — your threads, memory, and uploads are safe on the server.
          </p>
          <pre
            data-testid="caos-error-boundary-message"
            style={{
              marginTop: 18,
              padding: "10px 12px",
              fontSize: 11.5,
              fontFamily: "ui-monospace, Menlo, monospace",
              background: "rgba(0,0,0,0.45)",
              border: "1px solid rgba(248, 113, 113, 0.35)",
              borderRadius: 10,
              color: "rgba(252, 165, 165, 0.95)",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              maxHeight: 140,
              overflowY: "auto",
            }}
          >
            {message}
          </pre>
          <div style={{ display: "flex", gap: 10, marginTop: 18 }}>
            <button
              data-testid="caos-error-boundary-reload"
              onClick={this.handleReload}
              style={{
                flex: 1,
                padding: "10px 14px",
                background: "linear-gradient(135deg, #a78bfa 0%, #6366f1 100%)",
                border: "none",
                borderRadius: 10,
                color: "#0b0b14",
                fontWeight: 600,
                cursor: "pointer",
                fontSize: 13.5,
              }}
              type="button"
            >
              Reload CAOS
            </button>
            <button
              data-testid="caos-error-boundary-clear"
              onClick={this.handleClear}
              style={{
                padding: "10px 14px",
                background: "transparent",
                border: "1px solid rgba(167, 139, 250, 0.45)",
                borderRadius: 10,
                color: "rgba(226, 232, 240, 0.85)",
                cursor: "pointer",
                fontSize: 13,
              }}
              type="button"
              title="Clear local CAOS preferences and reload"
            >
              Clear local state
            </button>
          </div>
        </div>
      </div>
    );
  }
}

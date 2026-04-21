/**
 * Pre-login Welcome screen — matches Base44 parity.
 * Centered starfield + orb + feature grid + Take the Tour / Sign In / Continue as Guest.
 *
 * REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
 */
import { Brain, FileText, Mic, Search, Sparkles, LogIn } from "lucide-react";

export const LoginScreen = ({ onContinueAsGuest, onTakeTour }) => {
  const handleSignIn = () => {
    const redirectUrl = window.location.origin + "/auth/callback";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="welcome-pre-shell" data-testid="caos-welcome-pre-shell">
      <div className="welcome-pre-inner" data-testid="caos-welcome-pre-inner">
        <div className="welcome-pre-orb" data-testid="caos-welcome-pre-orb" aria-hidden="true">
          <Sparkles size={36} strokeWidth={1.5} />
        </div>
        <h1 className="welcome-pre-title" data-testid="caos-welcome-pre-title">CAOS</h1>
        <p className="welcome-pre-subtitle" data-testid="caos-welcome-pre-subtitle">
          Cognitive Adaptive Operating System
        </p>
        <p className="welcome-pre-tagline" data-testid="caos-welcome-pre-tagline">
          A personal AI platform that thinks, remembers, and works alongside you — not just answers questions.
        </p>

        <div className="welcome-pre-grid" data-testid="caos-welcome-pre-grid">
          <div className="welcome-pre-card" data-testid="caos-welcome-pre-card-memory">
            <Brain size={18} className="welcome-pre-card-icon" />
            <strong>Persistent Memory</strong>
            <span>Aria remembers what matters across every session.</span>
          </div>
          <div className="welcome-pre-card" data-testid="caos-welcome-pre-card-search">
            <Search size={18} className="welcome-pre-card-icon" />
            <strong>Web Search</strong>
            <span>Real-time knowledge from the internet, built in.</span>
          </div>
          <div className="welcome-pre-card" data-testid="caos-welcome-pre-card-files">
            <FileText size={18} className="welcome-pre-card-icon" />
            <strong>File Intelligence</strong>
            <span>Upload files, images, docs — Aria reads them all.</span>
          </div>
          <div className="welcome-pre-card" data-testid="caos-welcome-pre-card-voice">
            <Mic size={18} className="welcome-pre-card-icon" />
            <strong>Voice Ready</strong>
            <span>Speak to Aria or have her read responses aloud.</span>
          </div>
        </div>

        <button
          className="welcome-pre-primary-btn"
          data-testid="caos-welcome-pre-take-tour"
          onClick={onTakeTour}
          type="button"
        >
          <Sparkles size={16} />
          <span>Take the Tour</span>
        </button>

        <button
          className="welcome-pre-secondary-btn"
          data-testid="caos-welcome-pre-signin"
          onClick={handleSignIn}
          type="button"
        >
          <LogIn size={16} />
          <span>Sign In</span>
        </button>

        <button
          className="welcome-pre-ghost-btn"
          data-testid="caos-welcome-pre-guest"
          onClick={onContinueAsGuest}
          type="button"
        >
          Continue as Guest
        </button>

        <p className="welcome-pre-footer" data-testid="caos-welcome-pre-footer">
          CAOS · AI assistant platform · Aria AI persona · Memory system · Multi-provider inference (OpenAI, Claude, Gemini) · Web search · File intelligence · Voice I/O
        </p>
      </div>
    </div>
  );
};

import { UserRound, X } from "lucide-react";


export const ProfileDrawer = ({ isOpen, memoryCount, onClose, profile, runtimeSettings, sessionsCount, userEmail }) => {
  if (!isOpen) return null;

  return (
    <div className="drawer-overlay" data-testid="caos-profile-drawer-overlay">
      <aside className="drawer-shell" data-testid="caos-profile-drawer">
        <div className="drawer-header">
          <div className="context-card-heading">
            <UserRound size={16} />
            <h2 data-testid="caos-profile-drawer-heading">Profile</h2>
          </div>
          <button className="drawer-close-button" data-testid="caos-profile-drawer-close-button" onClick={onClose}>
            <X size={16} />
          </button>
        </div>

        <div className="drawer-card" data-testid="caos-profile-user-card">
          <span>Email</span>
          <strong data-testid="caos-profile-email-value">{profile?.user_email || userEmail}</strong>
        </div>
        <div className="drawer-card" data-testid="caos-profile-environment-card">
          <span>Environment</span>
          <strong data-testid="caos-profile-environment-value">{profile?.environment_name || "CAOS"}</strong>
        </div>
        <div className="drawer-card" data-testid="caos-profile-assistant-card">
          <span>Companion intelligence</span>
          <strong data-testid="caos-profile-assistant-value">{profile?.assistant_name || "Aria"}</strong>
        </div>
        <div className="drawer-card" data-testid="caos-profile-session-count-card">
          <span>Saved threads</span>
          <strong data-testid="caos-profile-session-count-value">{sessionsCount}</strong>
        </div>
        <div className="drawer-card" data-testid="caos-profile-memory-count-card">
          <span>Permanent memories</span>
          <strong data-testid="caos-profile-memory-count-value">{memoryCount}</strong>
        </div>
        <div className="drawer-card" data-testid="caos-profile-runtime-card">
          <span>Inference routing</span>
          <strong data-testid="caos-profile-runtime-value">{runtimeSettings?.key_source || "hybrid"}</strong>
        </div>
        <div className="drawer-card" data-testid="caos-profile-provider-card">
          <span>Active engine</span>
          <strong data-testid="caos-profile-provider-value">{runtimeSettings?.default_provider || "openai"} · {runtimeSettings?.default_model || "gpt-5.2"}</strong>
        </div>

        <div className="drawer-list" data-testid="caos-profile-memory-list">
          {(profile?.structured_memory || []).slice(0, 8).map((memory) => (
            <div className="drawer-list-item" data-testid={`caos-profile-memory-${memory.id}`} key={memory.id}>
              {memory.content}
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
};
import { useEffect, useState, useCallback } from "react";
import axios from "axios";
import { Check, X, Crown, Zap, Sparkles, Building2, Rocket, Star } from "lucide-react";
import { toast } from "sonner";

import { API } from "@/config/apiBase";
import "@/components/caos/connectors.css";

/**
 * PricingDrawer — 6-tier upgrade UI wired to Stripe Checkout.
 *
 * Flow:
 *   1. Fetch /billing/me on open → gets current tier + all available tiers.
 *   2. User picks a tier → POST /billing/checkout/<tier> with origin_url.
 *   3. Backend returns Stripe Checkout URL; we redirect the whole window
 *      (Stripe Checkout doesn't support iframe embedding, see playbook).
 *   4. Stripe redirects back to /?caos_billing=success&session_id=…
 *   5. App.js detects that param on load, polls /billing/status/<sid>
 *      until status="paid", shows toast, refreshes /billing/me.
 *
 * REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS,
 * THIS BREAKS THE AUTH. origin_url is built from window.location.origin.
 */

const TIER_VISUALS = {
  free:       { icon: <Sparkles size={18} />, accent: "rgba(167,139,250,0.55)" },
  novice:     { icon: <Zap size={18} />,       accent: "rgba(125,211,252,0.7)" },
  skilled:    { icon: <Star size={18} />,      accent: "rgba(134,239,172,0.7)" },
  elite:      { icon: <Crown size={18} />,     accent: "rgba(251,191,36,0.85)" },
  pro:        { icon: <Rocket size={18} />,    accent: "rgba(244,114,182,0.85)" },
  enterprise: { icon: <Building2 size={18} />, accent: "rgba(248,113,113,0.85)" },
};

export const PricingDrawer = ({ isOpen, onClose }) => {
  const [data, setData] = useState({ tier: "free", available_tiers: [], tier_expires_at: null, tier_name: "Free" });
  const [loading, setLoading] = useState(false);
  const [busyTier, setBusyTier] = useState(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const resp = await axios.get(`${API}/billing/me`, { withCredentials: true });
      setData(resp.data || data);
    } catch (err) {
      toast.error(err?.message || "Couldn't load pricing");
    } finally {
      setLoading(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { if (isOpen) refresh(); }, [isOpen, refresh]);

  const onUpgrade = async (tierId) => {
    setBusyTier(tierId);
    try {
      // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS,
      // THIS BREAKS THE AUTH.
      const originUrl = window.location.origin;
      const resp = await axios.post(
        `${API}/billing/checkout`,
        { tier_id: tierId, origin_url: originUrl },
        { withCredentials: true },
      );
      const url = resp.data?.url;
      if (!url) throw new Error("Backend returned no Stripe URL.");
      // Hard redirect — Stripe Checkout cannot live in an iframe.
      window.location.href = url;
    } catch (err) {
      toast.error(err?.response?.data?.detail || err?.message || "Checkout failed");
      setBusyTier(null);
    }
  };

  if (!isOpen) return null;

  const expiryNote = data.tier_expires_at
    ? `Active until ${new Date(data.tier_expires_at).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" })}`
    : "30-day pass per upgrade · stacks if you re-up";

  return (
    <div
      className="drawer-overlay"
      data-testid="caos-pricing-drawer-overlay"
      onClick={onClose}
      style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 219 }}
    >
      <aside
        className="connectors-drawer"
        data-testid="caos-pricing-drawer"
        onClick={(e) => e.stopPropagation()}
        style={{ width: "min(640px, 96vw)" }}
      >
        <div className="connectors-drawer-header">
          <div>
            <h2 className="connectors-drawer-title">Pricing & Tiers</h2>
            <p className="connectors-drawer-subtitle">
              Currently on <strong style={{ color: "#f5f3ff" }}>{data.tier_name}</strong> · {expiryNote}
            </p>
          </div>
          <button
            className="connectors-drawer-close"
            data-testid="caos-pricing-drawer-close"
            onClick={onClose} type="button" aria-label="Close pricing drawer"
          ><X size={16} /></button>
        </div>

        <div className="connectors-drawer-body">
          {loading && !data.available_tiers.length ? (
            <div style={{ padding: 24, color: "rgba(226,232,240,0.5)", fontSize: 13, textAlign: "center" }}>
              Loading tiers…
            </div>
          ) : null}

          {data.available_tiers.map((tier) => {
            const v = TIER_VISUALS[tier.id] || TIER_VISUALS.free;
            const current = data.tier === tier.id;
            const isFree = tier.id === "free";
            return (
              <div
                key={tier.id}
                className="connector-card"
                data-state={current ? "connected" : "not-connected"}
                data-testid={`caos-pricing-card-${tier.id}`}
                style={{ borderColor: current ? v.accent : undefined }}
              >
                <div className="connector-card-head">
                  <div className="connector-card-icon" style={{ background: `${v.accent.replace(",0.","").replace(")",",0.18)").replace("rgba(","rgba(")}`, color: v.accent }}>
                    {v.icon}
                  </div>
                  <div className="connector-card-meta">
                    <div className="connector-card-name">
                      {tier.name}
                      {current ? (
                        <span style={{
                          marginLeft: 8, padding: "2px 8px", borderRadius: 999,
                          background: v.accent, color: "#0b0b14",
                          fontSize: 10, fontWeight: 600, letterSpacing: "0.04em",
                        }}>CURRENT</span>
                      ) : null}
                    </div>
                    <div className="connector-card-status" data-tone={current ? "connected" : "default"}>
                      {isFree ? "$0 / month" : `$${tier.price_monthly} / month · ${PASS_NOTE}`}
                    </div>
                  </div>
                  <div style={{
                    fontSize: 22, fontWeight: 700, color: "#f5f3ff",
                    fontVariantNumeric: "tabular-nums",
                  }}>
                    {isFree ? "Free" : `$${tier.price_monthly}`}
                  </div>
                </div>
                <div className="connector-card-body" style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                  <div>{tier.description}</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 4 }}>
                    <span style={{ display: "inline-flex", gap: 4, alignItems: "center", padding: "2px 8px", borderRadius: 999, background: "rgba(167,139,250,0.12)", color: "#c4b5fd", fontSize: 10.5 }}>
                      <Check size={11} /> {(tier.daily_tokens / 1000).toLocaleString()}k tokens/day
                    </span>
                  </div>
                </div>
                <div className="connector-card-actions">
                  {current ? (
                    <span style={{ fontSize: 11.5, color: "rgba(134,239,172,0.92)", padding: "6px 0" }}>
                      You're on this tier.
                    </span>
                  ) : isFree ? (
                    <span style={{ fontSize: 11.5, color: "rgba(226,232,240,0.45)", padding: "6px 0" }}>
                      Default tier.
                    </span>
                  ) : (
                    <button
                      className="connector-action-btn"
                      data-variant="primary"
                      data-testid={`caos-pricing-card-${tier.id}-upgrade`}
                      disabled={busyTier === tier.id}
                      onClick={() => onUpgrade(tier.id)}
                      type="button"
                    >{busyTier === tier.id ? "Opening Stripe…" : `Upgrade to ${tier.name}`}</button>
                  )}
                </div>
              </div>
            );
          })}

          <div style={{ padding: "8px 4px 0 4px", fontSize: 10.5, color: "rgba(226,232,240,0.42)", lineHeight: 1.55 }}>
            All upgrades are 30-day passes (no auto-renew). Re-up anytime; days stack onto unused time.
            Test mode active — no real charges.
          </div>
        </div>
      </aside>
    </div>
  );
};

const PASS_NOTE = "30-day pass";

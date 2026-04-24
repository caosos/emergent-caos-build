import React, { useState, useEffect, useMemo } from "react";
import axios from "axios";
import { API } from "@/config/apiBase";
import "./AdminDashboard.css";

const fmtInt = (n) => {
  const v = Number(n) || 0;
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return String(v);
};

export const AdminDashboard = ({ onClose }) => {
  const [metrics, setMetrics] = useState(null);
  const [tokenUsage, setTokenUsage] = useState(null);
  const [dailyUsage, setDailyUsage] = useState(null);
  const [activity14d, setActivity14d] = useState(null);
  const [errors, setErrors] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [activeTab, setActiveTab] = useState("stats");

  const loadAll = async () => {
    try {
      setLoading(true);
      setLoadError(null);
      const [m, t, d, a, e] = await Promise.all([
        axios.get(`${API}/admin/dashboard/metrics`),
        axios.get(`${API}/admin/dashboard/token-usage`),
        axios.get(`${API}/admin/dashboard/daily-usage`),
        axios.get(`${API}/admin/dashboard/activity-14d`),
        axios.get(`${API}/admin/dashboard/errors`),
      ]);
      setMetrics(m.data);
      setTokenUsage(t.data);
      setDailyUsage(d.data);
      setActivity14d(a.data);
      setErrors(e.data);
    } catch (error) {
      console.error("Failed to load dashboard:", error);
      setLoadError(error.response?.data?.detail || error.message || "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAll(); }, []);

  // Auto-refresh every 30 s while dashboard is open
  useEffect(() => {
    const interval = setInterval(() => {
      if (!document.hidden) loadAll();
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="admin-dashboard-overlay" data-testid="caos-admin-dashboard-overlay">
        <div className="admin-dashboard-shell" data-testid="caos-admin-dashboard-shell">
          <div className="admin-dashboard-header">
            <h1>🛡️ CAOS Admin</h1>
            <button className="admin-close-btn" data-testid="caos-admin-close" onClick={onClose}>✕</button>
          </div>
          <div className="admin-loading">Loading dashboard…</div>
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="admin-dashboard-overlay" data-testid="caos-admin-dashboard-overlay">
        <div className="admin-dashboard-shell">
          <div className="admin-dashboard-header">
            <h1>🛡️ CAOS Admin</h1>
            <button className="admin-close-btn" data-testid="caos-admin-close" onClick={onClose}>✕</button>
          </div>
          <div className="admin-loading" style={{ color: "#ef4444", flexDirection: "column", gap: 14 }}>
            ❌ Error: {loadError}
            <button onClick={loadAll} style={{ padding: "8px 16px", background: "#8b5cf6", border: "none", borderRadius: 8, color: "#fff", cursor: "pointer" }}>Retry</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-dashboard-overlay" data-testid="caos-admin-dashboard-overlay">
      <div className="admin-dashboard-shell" data-testid="caos-admin-dashboard-shell">
        <div className="admin-dashboard-header">
          <div>
            <h1>🛡️ CAOS Admin</h1>
            <p className="admin-header-sub">System monitoring and diagnostics</p>
          </div>
          <button className="admin-close-btn" data-testid="caos-admin-close" onClick={onClose} title="Close">✕</button>
        </div>

        <div className="admin-tabs">
          <button className={`admin-tab ${activeTab === "stats" ? "active" : ""}`} data-testid="caos-admin-tab-stats" onClick={() => setActiveTab("stats")}>📊 Users & Stats</button>
          <button className={`admin-tab ${activeTab === "errors" ? "active" : ""}`} data-testid="caos-admin-tab-errors" onClick={() => setActiveTab("errors")}>⚡ Errors</button>
          <button className={`admin-tab ${activeTab === "timeline" ? "active" : ""}`} data-testid="caos-admin-tab-timeline" onClick={() => setActiveTab("timeline")}>🧭 Engine Timeline</button>
          <button className={`admin-tab ${activeTab === "users" ? "active" : ""}`} data-testid="caos-admin-tab-users" onClick={() => setActiveTab("users")}>👥 Top Users</button>
          <button className={`admin-tab ${activeTab === "usage" ? "active" : ""}`} data-testid="caos-admin-tab-usage" onClick={() => setActiveTab("usage")}>📈 Usage (30d)</button>
        </div>

        <div className="admin-dashboard-content">
          {activeTab === "stats" && <StatsTab metrics={metrics} activity14d={activity14d} onRefresh={loadAll} />}
          {activeTab === "errors" && <ErrorsTab errors={errors} />}
          {activeTab === "timeline" && <EngineTimelineTab />}
          {activeTab === "users" && <UsersTab tokenUsage={tokenUsage} tierDistribution={metrics?.users?.by_tier} />}
          {activeTab === "usage" && <UsageTab dailyUsage={dailyUsage} />}
        </div>
      </div>
    </div>
  );
};

// ─── Stats tab ──────────────────────────────────────────────────────────────

const StatsTab = ({ metrics, activity14d, onRefresh }) => {
  if (!metrics) return null;
  const live = metrics.live_status || {};
  const reg = metrics.registered_accounts || {};
  const sess = metrics.sessions || {};
  const login = metrics.login_methods || {};
  const tiers = metrics.users?.by_tier || {};
  const totalUsers = metrics.users?.total || 1;
  const totalLogins = (login.google || 0) + (login.guest || 0) || 1;

  return (
    <div className="admin-overview">
      <SectionHeader icon="🟢" title="Live Status" rightSlot={
        <button className="admin-refresh-btn" data-testid="caos-admin-refresh" onClick={onRefresh} title="Refresh">↻ Refresh</button>
      } />
      <div className="admin-stat-grid">
        <StatCard icon="👤" color="#34d399" label="Active Now (registered)" value={live.active_registered_1h} sub="sessions in last hour" testId="live-active-registered" />
        <StatCard icon="👥" color="#60a5fa" label="Active Now (guests)" value={live.active_guests_1h} sub="sessions in last hour" testId="live-active-guests" />
        <StatCard icon="↗" color="#a78bfa" label="Active Today" value={live.active_today} sub="all session types" testId="live-active-today" />
        <StatCard icon="↗" color="#a78bfa" label="Active This Week" value={live.active_week} sub="all session types" testId="live-active-week" />
      </div>

      <SectionHeader icon="👤" title="Registered Accounts" />
      <div className="admin-stat-grid">
        <StatCard icon="👤" color="#60a5fa" label="Total Registered" value={reg.total} testId="reg-total" />
        <StatCard icon="✉" color="#60a5fa" label="Ever Logged In" value={reg.ever_logged_in} sub="unique users" testId="reg-ever" />
        <StatCard icon="↗" color="#a78bfa" label="New This Month" value={reg.new_this_month} testId="reg-new-month" />
        <StatCard icon="↗" color="#f59e0b" label="New Today" value={reg.new_today} sub={`+${reg.new_this_week || 0} this week`} testId="reg-new-today" />
      </div>

      <SectionHeader icon="⏱" title="Sessions" />
      <div className="admin-stat-grid">
        <StatCard icon="⏱" color="#60a5fa" label="Total Sessions Ever" value={sess.total_ever} testId="sess-total" />
        <StatCard icon="👤" color="#a78bfa" label="Guest Sessions" value={sess.guest_sessions} sub="no account required" testId="sess-guest" />
        <StatCard icon="⏱" color="#22d3ee" label="Avg Session Length" value={`${sess.avg_session_minutes || 0}m`} sub="registered users" testId="sess-avg" />
        <StatCard icon="💬" color="#a78bfa" label="Total Threads" value={sess.total_threads} sub={`${sess.threads_today || 0} today · ${sess.threads_this_week || 0} this week`} testId="sess-threads" />
      </div>

      <div className="admin-dual-row">
        <DualChart title="New Registrations — Last 14 Days" data={activity14d?.registrations || []} color="#a78bfa" testId="chart-regs" />
        <DualChart title="Sessions Started — Last 14 Days" data={activity14d?.sessions || []} color="#22c55e" testId="chart-sess" />
      </div>

      <div className="admin-dual-row">
        <BarList
          title="Tier Distribution"
          icon="🏷"
          rows={Object.entries(tiers).map(([k, v]) => ({
            label: k.charAt(0).toUpperCase() + k.slice(1),
            value: v,
            pct: (v / totalUsers) * 100,
            className: `tier-${k}`,
          }))}
        />
        <BarList
          title="Login Methods"
          icon="🔐"
          rows={Object.entries(login).map(([k, v]) => ({
            label: k,
            value: v,
            pct: (v / totalLogins) * 100,
            className: k === "google" ? "tier-skilled" : "tier-free",
          }))}
        />
      </div>

      <div className="admin-cost-reference" data-testid="caos-admin-cost-reference">
        <strong>💡 Cost Reference (no billing active)</strong>
        <p>GPT-5.2 ~$5/1M input · Claude Sonnet 4.5 ~$3/1M input · Gemini 3 Flash ~$0.075/1M · Whisper STT ~$0.006/min · TTS ~$15/1M chars. Per-turn token cost tracking can be enabled by storing usage_tokens from message responses into token_usage records.</p>
      </div>
    </div>
  );
};

// ─── Errors tab ─────────────────────────────────────────────────────────────

const ErrorsTab = ({ errors }) => {
  if (!errors) return null;
  const byType = errors.by_type || {};
  const max = Math.max(1, ...Object.values(byType));

  return (
    <div className="admin-overview">
      <SectionHeader icon="⚡" title="Errors" />
      <div className="admin-stat-grid">
        <StatCard icon="⚡" color="#ef4444" label="Total Logged" value={errors.total_logged} testId="err-total" />
        <StatCard icon="⚡" color="#f59e0b" label="This Week" value={errors.this_week} testId="err-week" />
        <StatCard icon="⚡" color="#fbbf24" label="Today" value={errors.today} testId="err-today" />
      </div>

      <div className="admin-error-breakdown" data-testid="caos-admin-error-breakdown">
        <h3>Error Types Breakdown</h3>
        {Object.keys(byType).length === 0 ? (
          <div className="admin-empty-state">No errors logged yet. Filed support tickets with category=bug show up here.</div>
        ) : (
          <div className="admin-error-bars">
            {Object.entries(byType).map(([type, count]) => (
              <div key={type} className="admin-error-bar-row">
                <span className="admin-error-bar-label">{type}</span>
                <div className="admin-error-bar-container">
                  <div className="admin-error-bar" style={{ width: `${(count / max) * 100}%` }} />
                </div>
                <span className="admin-error-bar-count">{count}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

// ─── Top Users tab ──────────────────────────────────────────────────────────

const UsersTab = ({ tokenUsage }) => {
  if (!tokenUsage) return null;

  return (
    <div className="admin-users">
      <h3>Top Users by Token Usage (30 days)</h3>
      {tokenUsage.users?.length === 0 ? (
        <div className="admin-empty-state">No token usage recorded in the last 30 days.</div>
      ) : (
        <div className="admin-users-table-container">
          <table className="admin-users-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Tier</th>
                <th>Tokens Used</th>
                <th>Days Active</th>
              </tr>
            </thead>
            <tbody>
              {tokenUsage.users.slice(0, 50).map((u, idx) => (
                <tr key={idx}>
                  <td className="admin-user-email">{u.user_email}</td>
                  <td><span className={`admin-tier-badge tier-${u.tier}`}>{u.tier.charAt(0).toUpperCase() + u.tier.slice(1)}</span></td>
                  <td className="admin-token-count">{fmtInt(u.total_tokens)}</td>
                  <td>{u.days_active}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

// ─── Usage tab ──────────────────────────────────────────────────────────────

const UsageTab = ({ dailyUsage }) => {
  const chartData = useMemo(() => dailyUsage?.daily_stats || [], [dailyUsage]);
  if (!dailyUsage) return null;
  const maxTokens = Math.max(1, ...chartData.map((d) => d.total_tokens));

  return (
    <div className="admin-usage">
      <h3>Daily Token Usage (Last 30 Days)</h3>
      {chartData.length === 0 ? (
        <div className="admin-empty-state">No token usage recorded.</div>
      ) : (
        <>
          <div className="admin-usage-chart">
            {chartData.map((day, idx) => (
              <div key={idx} className="admin-usage-bar-wrapper">
                <div
                  className="admin-usage-bar"
                  style={{ height: `${(day.total_tokens / maxTokens) * 100}%` }}
                  title={`${day.date}: ${day.total_tokens.toLocaleString()} tokens`}
                />
                <div className="admin-usage-date">{day.date.slice(5)}</div>
              </div>
            ))}
          </div>
          <div className="admin-usage-legend">
            <div>Max: {maxTokens.toLocaleString()} tokens/day</div>
            <div>Sum: {chartData.reduce((s, d) => s + d.total_tokens, 0).toLocaleString()} tokens / 30d</div>
          </div>
        </>
      )}
    </div>
  );
};

// ─── Shared building blocks ─────────────────────────────────────────────────

const SectionHeader = ({ icon, title, rightSlot }) => (
  <div className="admin-section-header">
    <h2><span className="admin-section-icon">{icon}</span>{title}</h2>
    {rightSlot || null}
  </div>
);

const StatCard = ({ icon, color, label, value, sub, testId }) => (
  <div className="admin-stat-card" data-testid={`caos-admin-stat-${testId}`}>
    <div className="admin-stat-label" style={{ color }}>
      <span className="admin-stat-icon">{icon}</span> {label}
    </div>
    <div className="admin-stat-value">{typeof value === "number" ? fmtInt(value) : (value ?? "—")}</div>
    {sub ? <div className="admin-stat-sub">{sub}</div> : null}
  </div>
);

const DualChart = ({ title, data, color, testId }) => {
  const max = Math.max(1, ...data.map((d) => d.count || 0));
  return (
    <div className="admin-mini-chart" data-testid={`caos-admin-${testId}`}>
      <div className="admin-mini-chart-title">{title}</div>
      <div className="admin-mini-chart-bars">
        {data.map((d, idx) => (
          <div key={idx} className="admin-mini-chart-bar-wrap" title={`${d.date}: ${d.count}`}>
            <div className="admin-mini-chart-bar" style={{ height: `${((d.count || 0) / max) * 100}%`, background: color }} />
          </div>
        ))}
      </div>
      <div className="admin-mini-chart-footer">
        <span>{data[0]?.date?.slice(5) || "—"}</span>
        <span>Today</span>
      </div>
    </div>
  );
};

const BarList = ({ title, icon, rows }) => (
  <div className="admin-tier-distribution">
    <h3><span style={{ marginRight: 8 }}>{icon}</span>{title}</h3>
    <div className="admin-tier-bars">
      {rows.length === 0 ? <div className="admin-empty-state">No data.</div> : rows.map((r) => (
        <div key={r.label} className="admin-tier-bar-row">
          <div className="admin-tier-label">{r.label}</div>
          <div className="admin-tier-bar-container">
            <div className={`admin-tier-bar ${r.className || ""}`} style={{ width: `${Math.min(100, r.pct || 0)}%` }} />
          </div>
          <div className="admin-tier-count">{fmtInt(r.value)} ({(r.pct || 0).toFixed(1)}%)</div>
        </div>
      ))}
    </div>
  </div>
);

// ─── Engine Timeline tab ─────────────────────────────────────────────────────

const ENGINE_COLOR = { openai: "#34d399", anthropic: "#fcd34d", gemini: "#7dd3fc", xai: "#f9a8d4" };
const providerOf = (inf) => (inf || "").split(":")[0] || "";
const labelOf = (inf) => ({ openai: "OpenAI", anthropic: "Claude", gemini: "Gemini", xai: "Grok" }[providerOf(inf)] || providerOf(inf) || "—");

const EngineTimelineTab = () => {
  const [sessionId, setSessionId] = useState("");
  const [turns, setTurns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [loadError, setLoadError] = useState(null);
  const [recentSessions, setRecentSessions] = useState([]);

  useEffect(() => {
    axios.get(`${API}/caos/sessions?limit=30`)
      .then((res) => setRecentSessions(res.data || []))
      .catch(() => { /* non-fatal */ });
  }, []);

  const load = async (sid) => {
    if (!sid) return;
    setLoading(true);
    setLoadError(null);
    try {
      const res = await axios.get(`${API}/admin/dashboard/engine-timeline/${sid}`);
      setTurns(res.data?.turns || []);
    } catch (error) {
      setLoadError(error.response?.data?.detail || error.message || "Failed to load timeline");
      setTurns([]);
    } finally { setLoading(false); }
  };

  const distribution = useMemo(() => {
    const counts = {};
    turns.forEach((t) => {
      const p = providerOf(t.inference_provider);
      if (!p) return;
      counts[p] = (counts[p] || 0) + 1;
    });
    return counts;
  }, [turns]);
  const totalTurns = turns.length || 1;

  return (
    <div className="admin-overview" data-testid="caos-admin-engine-timeline">
      <SectionHeader icon="🧭" title="Engine Timeline" rightSlot={
        <span style={{ fontSize: 12, color: "rgba(255,255,255,0.5)" }}>Audit per-turn engine per thread</span>
      } />
      <div className="admin-timeline-controls">
        <input
          className="admin-timeline-input"
          data-testid="caos-admin-timeline-session-input"
          placeholder="Paste session_id or pick recent…"
          value={sessionId}
          onChange={(event) => setSessionId(event.target.value)}
          onKeyDown={(event) => { if (event.key === "Enter") load(sessionId.trim()); }}
        />
        <button className="admin-refresh-btn" data-testid="caos-admin-timeline-load" onClick={() => load(sessionId.trim())}>Load</button>
        <select
          className="admin-timeline-input"
          data-testid="caos-admin-timeline-recent"
          value=""
          onChange={(event) => { const v = event.target.value; if (v) { setSessionId(v); load(v); } }}
        >
          <option value="">Recent sessions…</option>
          {recentSessions.slice(0, 20).map((s) => (
            <option key={s.session_id} value={s.session_id}>{(s.title || "(no title)")} · {s.session_id.slice(0, 8)}</option>
          ))}
        </select>
      </div>

      {loading ? <div className="admin-empty-state">Loading timeline…</div> : null}
      {loadError ? <div className="admin-empty-state" style={{ color: "#fca5a5" }}>{loadError}</div> : null}
      {!loading && !loadError && !turns.length ? (
        <div className="admin-empty-state">Pick a session above to see which engine answered each turn.</div>
      ) : null}

      {turns.length > 0 ? (
        <>
          <div className="admin-stat-grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))" }}>
            {Object.entries(distribution).map(([provider, count]) => (
              <StatCard
                key={provider}
                icon="⚙"
                color={ENGINE_COLOR[provider] || "#94a3b8"}
                label={labelOf(provider)}
                value={count}
                sub={`${((count / totalTurns) * 100).toFixed(0)}% of turns`}
                testId={`timeline-engine-${provider}`}
              />
            ))}
          </div>
          <div className="admin-timeline-strip" data-testid="caos-admin-timeline-strip">
            {turns.map((turn) => {
              const provider = providerOf(turn.inference_provider);
              return (
                <div
                  key={turn.id}
                  className="admin-timeline-cell"
                  style={{ background: ENGINE_COLOR[provider] || "#475569" }}
                  title={`${labelOf(turn.inference_provider)} · ${turn.latency_ms || 0} ms\n${turn.preview}`}
                />
              );
            })}
          </div>
          <div className="admin-timeline-list">
            {turns.map((turn, idx) => {
              const provider = providerOf(turn.inference_provider);
              return (
                <div key={turn.id} className="admin-timeline-row" data-testid={`caos-admin-timeline-row-${idx}`}>
                  <span className="admin-timeline-idx">#{idx + 1}</span>
                  <span
                    className={`caos-engine-chip caos-engine-chip-${provider || "default"}`}
                    style={{ minWidth: 74, textAlign: "center" }}
                  >{labelOf(turn.inference_provider)}</span>
                  <span className="admin-timeline-latency">{turn.latency_ms || 0}ms</span>
                  {Array.isArray(turn.tools_used) && turn.tools_used.length > 0 ? (
                    <span className="caos-live-web-chip" style={{ margin: 0 }}>{turn.tools_used.join(" · ")}</span>
                  ) : <span style={{ width: 64 }} />}
                  <span className="admin-timeline-preview">{turn.preview || "(no preview)"}</span>
                </div>
              );
            })}
          </div>
        </>
      ) : null}
    </div>
  );
};


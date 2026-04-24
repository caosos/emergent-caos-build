import React, { useState, useEffect } from "react";
import axios from "axios";
import { API } from "@/config/apiBase";
import "./AdminDashboard.css";

export const AdminDashboard = ({ onClose }) => {
  const [metrics, setMetrics] = useState(null);
  const [tokenUsage, setTokenUsage] = useState(null);
  const [dailyUsage, setDailyUsage] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [metricsRes, tokenRes, dailyRes] = await Promise.all([
        axios.get(`${API}/admin/dashboard/metrics`),
        axios.get(`${API}/admin/dashboard/token-usage`),
        axios.get(`${API}/admin/dashboard/daily-usage`),
      ]);
      setMetrics(metricsRes.data);
      setTokenUsage(tokenRes.data);
      setDailyUsage(dailyRes.data);
    } catch (error) {
      console.error("Failed to load dashboard:", error);
      setError(error.response?.data?.detail || error.message || "Failed to load dashboard");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="admin-dashboard-overlay">
        <div className="admin-dashboard-shell">
          <div className="admin-dashboard-header">
            <h1>🛡️ Admin Dashboard</h1>
            <button className="admin-close-btn" onClick={onClose}>✕</button>
          </div>
          <div className="admin-loading">Loading dashboard...</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="admin-dashboard-overlay">
        <div className="admin-dashboard-shell">
          <div className="admin-dashboard-header">
            <h1>🛡️ Admin Dashboard</h1>
            <button className="admin-close-btn" onClick={onClose}>✕</button>
          </div>
          <div className="admin-loading" style={{ color: "#ef4444" }}>
            ❌ Error: {error}
            <button 
              onClick={loadDashboardData}
              style={{ 
                marginTop: "16px", 
                padding: "8px 16px", 
                background: "#8b5cf6", 
                border: "none", 
                borderRadius: "8px", 
                color: "#fff", 
                cursor: "pointer" 
              }}
            >
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="admin-dashboard-overlay">
      <div className="admin-dashboard-shell">
        <div className="admin-dashboard-header">
          <h1>🛡️ Admin Dashboard</h1>
          <button className="admin-close-btn" onClick={onClose}>✕</button>
        </div>

        <div className="admin-tabs">
          <button
            className={`admin-tab ${activeTab === "overview" ? "active" : ""}`}
            onClick={() => setActiveTab("overview")}
          >
            📊 Overview
          </button>
          <button
            className={`admin-tab ${activeTab === "users" ? "active" : ""}`}
            onClick={() => setActiveTab("users")}
          >
            👥 Users
          </button>
          <button
            className={`admin-tab ${activeTab === "usage" ? "active" : ""}`}
            onClick={() => setActiveTab("usage")}
          >
            📈 Usage
          </button>
        </div>

        <div className="admin-dashboard-content">
          {activeTab === "overview" && (
            <OverviewTab metrics={metrics} dailyUsage={dailyUsage} />
          )}
          {activeTab === "users" && (
            <UsersTab tokenUsage={tokenUsage} tierDistribution={metrics?.users?.by_tier} />
          )}
          {activeTab === "usage" && (
            <UsageTab dailyUsage={dailyUsage} />
          )}
        </div>
      </div>
    </div>
  );
};

const OverviewTab = ({ metrics, dailyUsage }) => {
  if (!metrics) return null;

  const formatNumber = (num) => {
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num?.toString() || "0";
  };

  return (
    <div className="admin-overview">
      <div className="admin-stat-grid">
        <div className="admin-stat-card">
          <div className="admin-stat-label">Total Users</div>
          <div className="admin-stat-value">{metrics.users.total}</div>
          <div className="admin-stat-sub">{metrics.users.active_7d} active (7d)</div>
        </div>

        <div className="admin-stat-card">
          <div className="admin-stat-label">Token Usage (30d)</div>
          <div className="admin-stat-value">{formatNumber(metrics.usage.total_tokens_30d)}</div>
          <div className="admin-stat-sub">{formatNumber(metrics.usage.total_requests_30d)} requests</div>
        </div>

        <div className="admin-stat-card">
          <div className="admin-stat-label">Total Sessions</div>
          <div className="admin-stat-value">{formatNumber(metrics.usage.total_sessions)}</div>
          <div className="admin-stat-sub">{formatNumber(metrics.usage.total_messages)} messages</div>
        </div>

        <div className="admin-stat-card">
          <div className="admin-stat-label">Support Tickets</div>
          <div className="admin-stat-value">{metrics.support.open_tickets}</div>
          <div className="admin-stat-sub">Open tickets</div>
        </div>
      </div>

      <div className="admin-tier-distribution">
        <h3>User Distribution by Tier</h3>
        <div className="admin-tier-bars">
          {Object.entries(metrics.users.by_tier || {}).map(([tier, count]) => {
            const percentage = ((count / metrics.users.total) * 100).toFixed(1);
            return (
              <div key={tier} className="admin-tier-bar-row">
                <div className="admin-tier-label">
                  {tier.charAt(0).toUpperCase() + tier.slice(1)}
                </div>
                <div className="admin-tier-bar-container">
                  <div 
                    className={`admin-tier-bar tier-${tier}`}
                    style={{ width: `${percentage}%` }}
                  />
                </div>
                <div className="admin-tier-count">{count} ({percentage}%)</div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

const UsersTab = ({ tokenUsage, tierDistribution }) => {
  if (!tokenUsage) return null;

  const formatNumber = (num) => {
    if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(2)}M`;
    if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`;
    return num;
  };

  return (
    <div className="admin-users">
      <h3>Top Users by Token Usage (30 days)</h3>
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
            {tokenUsage.users.slice(0, 50).map((user, idx) => (
              <tr key={idx}>
                <td className="admin-user-email">{user.user_email}</td>
                <td>
                  <span className={`admin-tier-badge tier-${user.tier}`}>
                    {user.tier.charAt(0).toUpperCase() + user.tier.slice(1)}
                  </span>
                </td>
                <td className="admin-token-count">{formatNumber(user.total_tokens)}</td>
                <td>{user.days_active}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

const UsageTab = ({ dailyUsage }) => {
  if (!dailyUsage) return null;

  const maxTokens = Math.max(...dailyUsage.daily_stats.map(d => d.total_tokens));

  return (
    <div className="admin-usage">
      <h3>Daily Token Usage (Last 30 Days)</h3>
      <div className="admin-usage-chart">
        {dailyUsage.daily_stats.map((day, idx) => {
          const height = (day.total_tokens / maxTokens) * 100;
          return (
            <div key={idx} className="admin-usage-bar-wrapper">
              <div 
                className="admin-usage-bar"
                style={{ height: `${height}%` }}
                title={`${day.date}: ${day.total_tokens.toLocaleString()} tokens`}
              />
              <div className="admin-usage-date">{day.date.slice(5)}</div>
            </div>
          );
        })}
      </div>
      <div className="admin-usage-legend">
        <div>Max: {maxTokens.toLocaleString()} tokens/day</div>
        <div>Total Users: {dailyUsage.daily_stats.reduce((sum, d) => sum + d.unique_users, 0)}</div>
      </div>
    </div>
  );
};

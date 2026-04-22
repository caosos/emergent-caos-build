import { useEffect, useState } from "react";
import axios from "axios";
import { Bug, CheckCircle2, Clock, Lightbulb, Loader2, RefreshCw, Sparkles, X } from "lucide-react";
import { toast } from "sonner";

import { API } from "@/config/apiBase";

const CATEGORY_ICONS = {
  bug: <Bug size={12} />,
  feature: <Lightbulb size={12} />,
  ux: <Sparkles size={12} />,
  other: <Sparkles size={12} />,
};

const STATUS_COLORS = {
  open: "#fde68a",
  in_progress: "#93c5fd",
  resolved: "#86efac",
  closed: "rgba(148, 163, 184, 0.7)",
};

const STATUS_LABELS = { open: "Open", in_progress: "In progress", resolved: "Resolved", closed: "Closed" };

const formatDate = (iso) => {
  try {
    const d = new Date(iso);
    return `${d.toLocaleDateString(undefined, { month: "short", day: "numeric" })} · ${d.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}`;
  } catch { return iso; }
};

export const SupportTicketsDrawer = ({ isAdmin, isOpen, onClose }) => {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState("all");

  const load = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/caos/support/tickets`);
      setTickets(response.data || []);
    } catch (error) {
      toast.error(`Load failed: ${(error?.response?.data?.detail || error?.message || "unknown").slice(0, 80)}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (isOpen) load(); }, [isOpen]);

  useEffect(() => {
    if (!isOpen) return undefined;
    const onEsc = (event) => { if (event.key === "Escape") onClose(); };
    document.addEventListener("keydown", onEsc);
    return () => document.removeEventListener("keydown", onEsc);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const updateStatus = async (id, nextStatus) => {
    try {
      await axios.patch(`${API}/caos/support/tickets/${id}`, { status: nextStatus });
      setTickets((prev) => prev.map((t) => (t.id === id ? { ...t, status: nextStatus } : t)));
      toast.success(`Ticket → ${STATUS_LABELS[nextStatus]}`);
    } catch (error) {
      toast.error(`Update failed: ${(error?.response?.data?.detail || error?.message || "unknown").slice(0, 80)}`);
    }
  };

  const filtered = statusFilter === "all" ? tickets : tickets.filter((t) => t.status === statusFilter);

  return (
    <div className="support-tickets-backdrop" data-testid="caos-support-tickets-backdrop" onClick={onClose}>
      <div className="support-tickets-modal" data-testid="caos-support-tickets-drawer" onClick={(event) => event.stopPropagation()}>
        <div className="support-tickets-header">
          <div>
            <h2 data-testid="caos-support-tickets-title">Support Tickets</h2>
            <p>{isAdmin ? "Admin view · all users" : "Your tickets"}</p>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <button className="support-tickets-refresh" data-testid="caos-support-tickets-refresh" onClick={load} type="button" title="Refresh">
              {loading ? <Loader2 size={14} className="spin" /> : <RefreshCw size={14} />}
            </button>
            <button className="support-tickets-close" data-testid="caos-support-tickets-close" onClick={onClose} type="button"><X size={16} /></button>
          </div>
        </div>
        <div className="support-tickets-filter-row" data-testid="caos-support-tickets-filter-row">
          {["all", "open", "in_progress", "resolved", "closed"].map((s) => (
            <button
              key={s}
              className={`support-tickets-filter-btn ${statusFilter === s ? "support-tickets-filter-btn-active" : ""}`}
              data-testid={`caos-support-tickets-filter-${s}`}
              onClick={() => setStatusFilter(s)}
              type="button"
            >{s === "all" ? "All" : STATUS_LABELS[s]} · <strong>{s === "all" ? tickets.length : tickets.filter((t) => t.status === s).length}</strong></button>
          ))}
        </div>
        <div className="support-tickets-body" data-testid="caos-support-tickets-body">
          {filtered.length === 0 ? (
            <div className="support-tickets-empty" data-testid="caos-support-tickets-empty">
              {loading ? "Loading tickets…" : "No tickets here yet. Aria will file them for you when you mention an issue."}
            </div>
          ) : (
            filtered.map((t) => (
              <article className="support-ticket-card" data-testid={`caos-support-ticket-${t.id}`} key={t.id}>
                <header className="support-ticket-card-header">
                  <span className="support-ticket-category" data-testid={`caos-support-ticket-category-${t.id}`}>
                    {CATEGORY_ICONS[t.category] || CATEGORY_ICONS.other} {t.category}
                  </span>
                  <span className="support-ticket-status" data-testid={`caos-support-ticket-status-${t.id}`} style={{ color: STATUS_COLORS[t.status] }}>
                    {t.status === "resolved" ? <CheckCircle2 size={12} /> : <Clock size={12} />}
                    {STATUS_LABELS[t.status]}
                  </span>
                  {t.source === "aria_filed" ? (
                    <span className="support-ticket-source" title="Filed automatically by Aria">via Aria</span>
                  ) : null}
                </header>
                <h4 data-testid={`caos-support-ticket-title-${t.id}`}>{t.title}</h4>
                <p data-testid={`caos-support-ticket-description-${t.id}`}>{t.description}</p>
                {isAdmin && t.user_email ? <small className="support-ticket-user">{t.user_email}</small> : null}
                <footer className="support-ticket-footer">
                  <span>{formatDate(t.created_at)}</span>
                  <div className="support-ticket-actions">
                    {t.status !== "in_progress" && t.status !== "resolved" ? (
                      <button data-testid={`caos-support-ticket-progress-${t.id}`} onClick={() => updateStatus(t.id, "in_progress")} type="button">In progress</button>
                    ) : null}
                    {t.status !== "resolved" ? (
                      <button data-testid={`caos-support-ticket-resolve-${t.id}`} onClick={() => updateStatus(t.id, "resolved")} type="button">Resolve</button>
                    ) : null}
                    {t.status !== "closed" ? (
                      <button data-testid={`caos-support-ticket-close-${t.id}`} onClick={() => updateStatus(t.id, "closed")} type="button">Close</button>
                    ) : null}
                  </div>
                </footer>
              </article>
            ))
          )}
        </div>
      </div>
    </div>
  );
};

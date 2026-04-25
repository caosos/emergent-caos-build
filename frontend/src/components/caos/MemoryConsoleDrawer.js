import axios from "axios";
import { Brain, Check, ChevronDown, FileText, ShieldAlert, Trash2, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";

import { API } from "@/config/apiBase";

/**
 * Memory Console — Aria's brain, made visible.
 *
 * Phase 1 = read-only audit. Phase 2 = autonomous extraction + override.
 * Renders a left-hand bin nav + a right-hand atom list. Each atom card
 * surfaces source mode, confidence, evidence count, and (for DERIVED
 * candidates from the autonomous extractor) Confirm / Edit-bin / Delete
 * controls so the user is always in charge of what Aria remembers.
 */

// Color tint per source mode (truth taxonomy: USER_EXPLICIT → green,
// OBSERVED → blue, DERIVED → purple, SYSTEM → grey).
const SOURCE_TONE = {
  USER_EXPLICIT: { label: "USER-STATED", className: "memory-source-user" },
  OBSERVED: { label: "OBSERVED", className: "memory-source-observed" },
  DERIVED: { label: "DERIVED", className: "memory-source-derived" },
  SYSTEM: { label: "SYSTEM", className: "memory-source-system" },
};

const SENSITIVITY_TONE = {
  high: { label: "HIGH", className: "memory-sens-high" },
  medium: { label: "MED", className: "memory-sens-medium" },
  normal: { label: "NORMAL", className: "memory-sens-normal" },
};

// Order bins so the most authoritative (governance/identity/projects) appear
// first in the tab nav. Mirrors the blueprint's "Tier 1 — Stable Foundation".
const BIN_ORDER = [
  "IDENTITY_FACT",
  "ACTIVE_PROJECT",
  "GOVERNANCE_RULE",
  "OPERATING_PREFERENCE",
  "RELATIONSHIP_BOUNDARY",
  "DOMAIN_CONTEXT",
  "TECHNICAL_STATE",
  "BEHAVIORAL_PATTERN",
  "DERIVED_TRAIT",
  "LEARNING_PROFILE",
  "REAL_WORLD_CONTEXT",
  "RISK_SIGNAL",
  "COUNTEREVIDENCE",
  "GENERAL",
];

const BIN_LABELS = {
  IDENTITY_FACT: "Identity",
  ACTIVE_PROJECT: "Projects",
  GOVERNANCE_RULE: "Governance",
  OPERATING_PREFERENCE: "Preferences",
  RELATIONSHIP_BOUNDARY: "Relationship",
  DOMAIN_CONTEXT: "Domains",
  TECHNICAL_STATE: "Tech State",
  BEHAVIORAL_PATTERN: "Behavioral",
  DERIVED_TRAIT: "Traits",
  LEARNING_PROFILE: "Learning",
  REAL_WORLD_CONTEXT: "Real-world",
  RISK_SIGNAL: "Risk",
  COUNTEREVIDENCE: "Counter",
  GENERAL: "Unclassified",
};

const formatDate = (iso) => {
  if (!iso) return "—";
  try {
    const d = typeof iso === "string" ? new Date(iso) : iso;
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  } catch {
    return "—";
  }
};

export const MemoryConsoleDrawer = ({ isOpen, onClose, userEmail }) => {
  const [atoms, setAtoms] = useState([]);
  const [binCounts, setBinCounts] = useState({});
  const [binRegistry, setBinRegistry] = useState({});
  const [activeBin, setActiveBin] = useState("IDENTITY_FACT");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [evidenceFor, setEvidenceFor] = useState(null);
  const [evidenceList, setEvidenceList] = useState([]);

  const refresh = async () => {
    if (!userEmail) return;
    setLoading(true);
    setError("");
    try {
      const resp = await axios.get(`${API}/caos/memory/atoms`, {
        params: { user_email: userEmail },
        withCredentials: true,
      });
      setAtoms(resp.data?.atoms || []);
      setBinCounts(resp.data?.bin_counts || {});
      setBinRegistry(resp.data?.bin_registry || {});
    } catch (issue) {
      setError(issue?.response?.data?.detail || issue?.message || "Failed to load memory");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen, userEmail]);

  const filteredAtoms = useMemo(
    () => atoms.filter((a) => a.bin_name === activeBin),
    [atoms, activeBin]
  );

  const totalAtoms = atoms.length;

  const handleConfirm = async (atomId) => {
    try {
      await axios.post(
        `${API}/caos/memory/atoms/${atomId}/confirm`,
        { user_email: userEmail },
        { withCredentials: true }
      );
      toast.success("Atom confirmed — promoted to user-stated.");
      refresh();
    } catch (issue) {
      toast.error(issue?.response?.data?.detail || "Confirm failed");
    }
  };

  const handleDelete = async (atomId, summary) => {
    if (!window.confirm(`Forget this memory?\n\n"${summary || atomId}"`)) return;
    try {
      await axios.delete(`${API}/caos/memory/atoms/${atomId}`, {
        params: { user_email: userEmail },
        withCredentials: true,
      });
      toast.success("Memory deleted.");
      refresh();
    } catch (issue) {
      toast.error(issue?.response?.data?.detail || "Delete failed");
    }
  };

  const handleReclassify = async (atomId, newBin) => {
    try {
      await axios.patch(
        `${API}/caos/memory/atoms/${atomId}`,
        { user_email: userEmail, bin_name: newBin },
        { withCredentials: true }
      );
      toast.success(`Reclassified → ${BIN_LABELS[newBin] || newBin}`);
      refresh();
    } catch (issue) {
      toast.error(issue?.response?.data?.detail || "Reclassify failed");
    }
  };

  const openEvidence = async (atom) => {
    setEvidenceFor(atom);
    setEvidenceList([]);
    try {
      const resp = await axios.get(`${API}/caos/memory/atoms/${atom.id}/evidence`, {
        params: { user_email: userEmail },
        withCredentials: true,
      });
      setEvidenceList(resp.data?.evidence || []);
    } catch (issue) {
      toast.error(issue?.response?.data?.detail || "Evidence fetch failed");
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="memory-console-backdrop"
      data-testid="caos-memory-console-backdrop"
      onClick={onClose}
    >
      <div
        className="memory-console-drawer"
        data-testid="caos-memory-console-drawer"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
      >
        <div className="memory-console-header" data-testid="caos-memory-console-header">
          <div className="memory-console-header-title">
            <Brain size={16} />
            <h2 data-testid="caos-memory-console-title">Memory Console</h2>
            <span className="memory-console-total" data-testid="caos-memory-console-total">
              {totalAtoms} atom{totalAtoms === 1 ? "" : "s"}
            </span>
          </div>
          <button
            aria-label="Close memory console"
            className="drawer-close-button"
            data-testid="caos-memory-console-close"
            onClick={onClose}
            type="button"
          >
            <X size={14} />
          </button>
        </div>

        <div className="memory-console-body">
          <nav className="memory-console-nav" data-testid="caos-memory-console-nav">
            {BIN_ORDER.map((binId) => {
              const count = binCounts[binId] || 0;
              const reg = binRegistry[binId] || {};
              return (
                <button
                  className={`memory-console-bin-tab ${activeBin === binId ? "memory-console-bin-tab-active" : ""}`}
                  data-testid={`caos-memory-bin-${binId}`}
                  key={binId}
                  onClick={() => setActiveBin(binId)}
                  title={reg.description || ""}
                  type="button"
                >
                  <span className="memory-console-bin-label">{BIN_LABELS[binId] || binId}</span>
                  <span className="memory-console-bin-count">{count}</span>
                </button>
              );
            })}
          </nav>

          <article className="memory-console-list" data-testid="caos-memory-console-list">
            {error ? (
              <div className="memory-console-error" data-testid="caos-memory-console-error">{error}</div>
            ) : null}
            {loading ? (
              <div className="memory-console-loading" data-testid="caos-memory-console-loading">Loading…</div>
            ) : null}
            {!loading && !error ? (
              <div className="memory-console-bin-header" data-testid="caos-memory-active-bin-header">
                <h3>{BIN_LABELS[activeBin] || activeBin}</h3>
                <p>{binRegistry[activeBin]?.description || ""}</p>
              </div>
            ) : null}
            {!loading && !error && filteredAtoms.length === 0 ? (
              <div className="memory-console-empty" data-testid="caos-memory-console-empty">
                Aria hasn&apos;t saved anything in this bin yet. Keep chatting — the
                autonomous extractor will fill it in as patterns emerge.
              </div>
            ) : null}
            {filteredAtoms.map((atom) => (
              <AtomCard
                atom={atom}
                key={atom.id}
                onConfirm={() => handleConfirm(atom.id)}
                onDelete={() => handleDelete(atom.id, atom.summary || atom.content)}
                onReclassify={(newBin) => handleReclassify(atom.id, newBin)}
                onShowEvidence={() => openEvidence(atom)}
              />
            ))}
          </article>
        </div>

        {evidenceFor ? (
          <EvidencePanel
            atom={evidenceFor}
            evidence={evidenceList}
            onClose={() => { setEvidenceFor(null); setEvidenceList([]); }}
          />
        ) : null}
      </div>
    </div>
  );
};


const AtomCard = ({ atom, onConfirm, onDelete, onReclassify, onShowEvidence }) => {
  const [showReclassify, setShowReclassify] = useState(false);
  const tone = SOURCE_TONE[atom.source_mode] || SOURCE_TONE.SYSTEM;
  const sens = SENSITIVITY_TONE[atom.sensitivity] || SENSITIVITY_TONE.normal;
  const confidencePct = Math.round((atom.confidence || 0) * 100);
  const isCandidate = !atom.user_confirmed && atom.source_mode === "DERIVED";

  return (
    <div
      className={`memory-atom-card ${isCandidate ? "memory-atom-card-candidate" : ""}`}
      data-testid={`caos-memory-atom-${atom.id}`}
    >
      <div className="memory-atom-content" data-testid={`caos-memory-atom-content-${atom.id}`}>
        {atom.content}
      </div>
      <div className="memory-atom-meta" data-testid={`caos-memory-atom-meta-${atom.id}`}>
        <span className={`memory-source-pill ${tone.className}`} data-testid={`caos-memory-atom-source-${atom.id}`}>
          {tone.label}
        </span>
        <span className="memory-confidence-pill" title={`Confidence ${confidencePct}%`}>
          {confidencePct}%
        </span>
        {atom.evidence_count > 0 ? (
          <button
            className="memory-evidence-pill"
            data-testid={`caos-memory-atom-evidence-${atom.id}`}
            onClick={onShowEvidence}
            type="button"
          >
            <FileText size={10} />
            {atom.evidence_count} evidence
          </button>
        ) : null}
        {atom.sensitivity && atom.sensitivity !== "normal" ? (
          <span className={`memory-sens-pill ${sens.className}`} title={`Sensitivity ${sens.label}`}>
            <ShieldAlert size={10} /> {sens.label}
          </span>
        ) : null}
        <span className="memory-priority-pill" title="Injection priority (higher = more often included in context)">
          P{atom.priority}
        </span>
        <span className="memory-date-pill" title={`Last validated ${atom.last_validated_at || atom.updated_at}`}>
          {formatDate(atom.updated_at)}
        </span>
      </div>
      <div className="memory-atom-actions" data-testid={`caos-memory-atom-actions-${atom.id}`}>
        {isCandidate ? (
          <button
            className="memory-atom-confirm-btn"
            data-testid={`caos-memory-atom-confirm-${atom.id}`}
            onClick={onConfirm}
            type="button"
          >
            <Check size={11} /> Confirm
          </button>
        ) : null}
        <div className="memory-atom-reclassify-wrap">
          <button
            className="memory-atom-reclassify-btn"
            data-testid={`caos-memory-atom-reclassify-${atom.id}`}
            onClick={() => setShowReclassify((v) => !v)}
            type="button"
          >
            Reclassify <ChevronDown size={10} />
          </button>
          {showReclassify ? (
            <div className="memory-atom-reclassify-menu" data-testid={`caos-memory-atom-reclassify-menu-${atom.id}`}>
              {BIN_ORDER.filter((b) => b !== atom.bin_name && b !== "GENERAL").map((b) => (
                <button
                  className="memory-atom-reclassify-option"
                  data-testid={`caos-memory-atom-reclassify-option-${atom.id}-${b}`}
                  key={b}
                  onClick={() => { setShowReclassify(false); onReclassify(b); }}
                  type="button"
                >
                  {BIN_LABELS[b] || b}
                </button>
              ))}
            </div>
          ) : null}
        </div>
        <button
          className="memory-atom-delete-btn"
          data-testid={`caos-memory-atom-delete-${atom.id}`}
          onClick={onDelete}
          type="button"
        >
          <Trash2 size={11} /> Forget
        </button>
      </div>
    </div>
  );
};


const EvidencePanel = ({ atom, evidence, onClose }) => (
  <div className="memory-evidence-panel" data-testid="caos-memory-evidence-panel">
    <div className="memory-evidence-header">
      <div>
        <h4>Evidence trail</h4>
        <p className="memory-evidence-subject">{atom.summary || atom.content}</p>
      </div>
      <button
        aria-label="Close evidence"
        className="memory-evidence-close"
        data-testid="caos-memory-evidence-close"
        onClick={onClose}
        type="button"
      >
        <X size={12} />
      </button>
    </div>
    <div className="memory-evidence-body">
      {evidence.length === 0 ? (
        <div className="memory-console-empty">No evidence anchors recorded yet.</div>
      ) : null}
      {evidence.map((e) => (
        <div className="memory-evidence-row" data-testid={`caos-memory-evidence-${e.id}`} key={e.id}>
          <div className="memory-evidence-meta">
            <span className="memory-evidence-type">{e.source_type}</span>
            <span className="memory-evidence-strength">strength {Math.round((e.evidence_strength || 0) * 100)}%</span>
            <span className="memory-evidence-date">{formatDate(e.created_at)}</span>
          </div>
          <div className="memory-evidence-quote">{e.quote_or_anchor}</div>
          {e.source_ref ? (
            <div className="memory-evidence-ref" title="Source reference">ref: {e.source_ref}</div>
          ) : null}
        </div>
      ))}
    </div>
  </div>
);

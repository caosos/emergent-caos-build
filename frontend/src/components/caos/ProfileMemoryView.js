import { useEffect, useRef, useState } from "react";
import { Brain, Pencil, Save, Trash2, X } from "lucide-react";
import { toast } from "sonner";

export const ProfileMemoryView = ({ deleteMemory, isOpen, memories, onClose, saveMemory, updateMemory }) => {
  const [draft, setDraft] = useState("");
  const [editingId, setEditingId] = useState(null);
  const [editDraft, setEditDraft] = useState("");
  const shellRef = useRef(null);

  useEffect(() => {
    if (!isOpen) return undefined;
    const handler = (event) => {
      if (shellRef.current && !shellRef.current.contains(event.target)) onClose();
    };
    const esc = (event) => { if (event.key === "Escape") onClose(); };
    document.addEventListener("mousedown", handler);
    document.addEventListener("keydown", esc);
    return () => {
      document.removeEventListener("mousedown", handler);
      document.removeEventListener("keydown", esc);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const handleSave = async () => {
    if (!draft.trim()) return;
    try {
      await saveMemory?.({ content: draft.trim() });
      toast.success("Memory saved");
      setDraft("");
    } catch (error) {
      toast.error(`Save failed: ${(error?.message || "unknown").slice(0, 60)}`);
    }
  };

  const handleDelete = async (id) => {
    try { await deleteMemory?.(id); toast.success("Memory removed"); }
    catch (error) { toast.error(`Delete failed: ${(error?.message || "unknown").slice(0, 60)}`); }
  };

  const commitEdit = async (id) => {
    if (!editDraft.trim()) { setEditingId(null); return; }
    try {
      await updateMemory?.(id, { content: editDraft.trim() });
      toast.success("Memory updated");
      setEditingId(null);
      setEditDraft("");
    } catch (error) { toast.error(`Update failed: ${(error?.message || "unknown").slice(0, 60)}`); }
  };

  return (
    <div className="voice-settings-overlay" data-testid="caos-memory-view-overlay">
      <div className="voice-settings-shell voice-settings-shell-wide" data-testid="caos-memory-view" ref={shellRef}>
        <div className="voice-settings-header">
          <div className="voice-settings-heading"><Brain size={16} /><h2 data-testid="caos-memory-view-title">Permanent Memories</h2></div>
          <button className="drawer-close-button" data-testid="caos-memory-view-close" onClick={onClose} type="button"><X size={16} /></button>
        </div>
        <div className="voice-settings-body">
          <div className="voice-settings-section">
            <h3>Add a memory</h3>
            <div className="memory-view-add-row">
              <input
                className="profile-birthday-input memory-view-add-input"
                data-testid="caos-memory-view-add-input"
                onChange={(event) => setDraft(event.target.value)}
                onKeyDown={(event) => { if (event.key === "Enter") handleSave(); }}
                placeholder="Something I should remember…"
                value={draft}
              />
              <button className="voice-settings-save memory-view-add-btn" data-testid="caos-memory-view-add-save" onClick={handleSave} type="button">
                <Save size={12} />Save
              </button>
            </div>
          </div>
          <div className="voice-settings-section">
            <h3>Saved ({memories?.length || 0})</h3>
            <div className="memory-view-list" data-testid="caos-memory-view-list">
              {memories?.length === 0 ? (
                <p className="profile-files-empty" data-testid="caos-memory-view-empty">No memories yet. Say "remember that…" in chat or add one above.</p>
              ) : null}
              {memories?.map((memory) => (
                <div className="memory-view-item" data-testid={`caos-memory-view-item-${memory.id}`} key={memory.id}>
                  {editingId === memory.id ? (
                    <>
                      <input
                        autoFocus
                        className="profile-birthday-input memory-view-edit-input"
                        data-testid={`caos-memory-view-edit-input-${memory.id}`}
                        onChange={(event) => setEditDraft(event.target.value)}
                        onKeyDown={(event) => { if (event.key === "Enter") commitEdit(memory.id); if (event.key === "Escape") setEditingId(null); }}
                        value={editDraft}
                      />
                      <button className="memory-view-action" data-testid={`caos-memory-view-edit-save-${memory.id}`} onClick={() => commitEdit(memory.id)} type="button"><Save size={12} /></button>
                      <button className="memory-view-action" data-testid={`caos-memory-view-edit-cancel-${memory.id}`} onClick={() => { setEditingId(null); setEditDraft(""); }} type="button"><X size={12} /></button>
                    </>
                  ) : (
                    <>
                      <p data-testid={`caos-memory-view-item-text-${memory.id}`}>{memory.content}</p>
                      <button className="memory-view-action" data-testid={`caos-memory-view-edit-${memory.id}`} onClick={() => { setEditingId(memory.id); setEditDraft(memory.content); }} type="button"><Pencil size={12} /></button>
                      <button className="memory-view-action memory-view-action-danger" data-testid={`caos-memory-view-delete-${memory.id}`} onClick={() => handleDelete(memory.id)} type="button"><Trash2 size={12} /></button>
                    </>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

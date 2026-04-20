import { useCallback } from "react";
import axios from "axios";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

/**
 * Memory CRUD hook — save/update/delete personal facts & structured memories.
 * Extracted from useCaosShell.js for GOV v1.2 file-size compliance.
 */
export const useMemoryCrud = ({ userEmail, loadProfile, setBusy, setError, setStatus }) => {
  const saveMemory = useCallback(async (content, binName = "general") => {
    if (!content.trim()) return;
    setBusy(true);
    setError("");
    try {
      await axios.post(`${API}/caos/memory/save`, {
        user_email: userEmail,
        content,
        bin_name: binName,
      });
      await loadProfile();
      setStatus(`Saved ${binName === "personal_facts" ? "personal fact" : "memory"}.`);
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Saving memory failed.";
      setError(message);
      setStatus(`Saving memory failed: ${message}`);
    } finally {
      setBusy(false);
    }
  }, [loadProfile, setBusy, setError, setStatus, userEmail]);

  const updateMemory = useCallback(async (memoryId, changes) => {
    setBusy(true);
    setError("");
    try {
      await axios.patch(`${API}/caos/memory/${memoryId}`, {
        user_email: userEmail,
        ...changes,
      });
      await loadProfile();
      setStatus("Memory updated.");
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Updating memory failed.";
      setError(message);
      setStatus(`Updating memory failed: ${message}`);
    } finally {
      setBusy(false);
    }
  }, [loadProfile, setBusy, setError, setStatus, userEmail]);

  const deleteMemory = useCallback(async (memoryId) => {
    setBusy(true);
    setError("");
    try {
      await axios.delete(`${API}/caos/memory/${memoryId}`, { params: { user_email: userEmail } });
      await loadProfile();
      setStatus("Memory deleted.");
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Deleting memory failed.";
      setError(message);
      setStatus(`Deleting memory failed: ${message}`);
    } finally {
      setBusy(false);
    }
  }, [loadProfile, setBusy, setError, setStatus, userEmail]);

  return { saveMemory, updateMemory, deleteMemory };
};

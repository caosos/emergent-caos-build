import { useCallback } from "react";
import axios from "axios";

import { API } from "@/config/apiBase";

/**
 * Files & Links CRUD hook — upload files, save link records, and re-load the
 * current user's file list. Extracted from useCaosShell.js for GOV v1.2.
 */
export const useFilesCrud = ({ userEmail, currentSession, loadFiles, loadSessionLinks, setBusy, setError, setStatus }) => {
  const uploadFile = useCallback(async (file) => {
    if (!file) return;
    const form = new FormData();
    form.append("user_email", userEmail);
    if (currentSession?.session_id) form.append("session_id", currentSession.session_id);
    form.append("file", file);
    setBusy(true);
    setError("");
    try {
      const response = await axios.post(`${API}/caos/files/upload`, form);
      await loadFiles();
      setStatus(`Uploaded ${file.name}.`);
      return response.data;
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Upload failed.";
      setError(message);
      setStatus(`Upload failed: ${message}`);
      throw issue;
    } finally {
      setBusy(false);
    }
  }, [currentSession, loadFiles, setBusy, setError, setStatus, userEmail]);

  const saveLink = useCallback(async (url, label) => {
    if (!url.trim()) return null;
    if (!currentSession?.session_id) {
      setStatus("Open a thread before saving links.");
      return null;
    }
    setBusy(true);
    setError("");
    try {
      const response = await axios.post(`${API}/caos/sessions/${currentSession.session_id}/links`, {
        url,
        label: label?.trim() || null,
        source: "manual",
      });
      await loadSessionLinks?.(currentSession.session_id);
      await loadFiles();
      setStatus(`Saved link ${(response.data?.label || label || url).slice(0, 60)}.`);
      return response.data;
    } catch (issue) {
      const message = issue?.response?.data?.detail || issue?.message || "Saving link failed.";
      setError(message);
      setStatus(`Saving link failed: ${message}`);
      return null;
    } finally {
      setBusy(false);
    }
  }, [currentSession, loadFiles, loadSessionLinks, setBusy, setError, setStatus, userEmail]);

  return { uploadFile, saveLink };
};

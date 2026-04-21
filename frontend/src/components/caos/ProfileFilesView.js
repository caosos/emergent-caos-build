import { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { ExternalLink, FileText, Image as ImageIcon, Search } from "lucide-react";

import { API } from "@/config/apiBase";

const TYPE_FILTERS = {
  files: (record) => !record.mime_type?.startsWith("image/") && record.kind !== "link",
  photos: (record) => record.mime_type?.startsWith("image/"),
  links: (record) => record.kind === "link" || record.type === "link",
};

const HEADINGS = { files: "Files", photos: "Photos", links: "Links" };
const EMPTY_COPY = {
  files: "No files yet. Attach one from the composer + menu.",
  photos: "No photos yet. Drop an image in the composer.",
  links: "No links yet. Shared links show up here.",
};

export const ProfileFilesView = ({ kind, profile, userEmail }) => {
  const [records, setRecords] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const email = profile?.user_email || userEmail;
    if (!email) return;
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const response = await axios.get(`${API}/caos/files`, { params: { user_email: email } });
        if (!cancelled) setRecords(response.data?.items || []);
      } catch { if (!cancelled) setRecords([]); }
      finally { if (!cancelled) setLoading(false); }
    })();
    return () => { cancelled = true; };
  }, [profile?.user_email, userEmail]);

  const filtered = useMemo(() => {
    const filterFn = TYPE_FILTERS[kind] || (() => true);
    return records.filter((record) => {
      if (!filterFn(record)) return false;
      if (!query.trim()) return true;
      const haystack = `${record.name || ""} ${record.url || ""} ${record.original_name || ""}`.toLowerCase();
      return haystack.includes(query.toLowerCase());
    });
  }, [kind, query, records]);

  return (
    <div className="profile-files-view" data-testid={`caos-profile-files-view-${kind}`}>
      <div className="profile-files-heading" data-testid={`caos-profile-files-heading-${kind}`}>
        {kind === "photos" ? <ImageIcon size={14} /> : kind === "links" ? <ExternalLink size={14} /> : <FileText size={14} />}
        <h3 data-testid={`caos-profile-files-title-${kind}`}>{HEADINGS[kind]}</h3>
        <span className="profile-files-count" data-testid={`caos-profile-files-count-${kind}`}>
          {loading ? "Loading…" : `${filtered.length}`}
        </span>
      </div>
      <label className="profile-files-search" data-testid={`caos-profile-files-search-row-${kind}`}>
        <Search size={13} />
        <input
          data-testid={`caos-profile-files-search-input-${kind}`}
          onChange={(event) => setQuery(event.target.value)}
          placeholder={`Search ${HEADINGS[kind].toLowerCase()}`}
          value={query}
        />
      </label>
      <div className="profile-files-list" data-testid={`caos-profile-files-list-${kind}`}>
        {!loading && filtered.length === 0 ? (
          <p className="profile-files-empty" data-testid={`caos-profile-files-empty-${kind}`}>{EMPTY_COPY[kind]}</p>
        ) : null}
        {filtered.map((record) => (
          <a
            className="profile-files-card"
            data-testid={`caos-profile-files-card-${record.id || record.file_id || record.url}`}
            href={record.url || record.public_url || "#"}
            key={record.id || record.file_id || record.url}
            rel="noreferrer"
            target="_blank"
          >
            <strong data-testid={`caos-profile-files-card-title-${record.id || record.url}`}>
              {record.name || record.original_name || record.url || "Untitled"}
            </strong>
            <span data-testid={`caos-profile-files-card-meta-${record.id || record.url}`}>
              {record.mime_type || record.kind || "file"}
              {record.size ? ` · ${Math.round((record.size || 0) / 1024)} KB` : ""}
            </span>
          </a>
        ))}
      </div>
    </div>
  );
};

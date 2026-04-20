import { useEffect, useRef, useState } from "react";
import { Copy, CornerDownLeft, Plus, Volume2, X } from "lucide-react";
import { toast } from "sonner";

const ALL_EMOJIS = [
  "👍", "❤️", "😂", "🤔", "👀", "🔥", "😊", "🎯", "✨", "💯",
  "🙌", "👏", "💪", "🎉", "⭐", "💡", "🚀", "🌟", "💖", "😍",
  "🤗", "😎", "🤩", "😢", "😭", "🙏", "👌", "✅", "❌", "⚡", "💥",
];
const DEFAULT_VISIBLE = ALL_EMOJIS.slice(0, 7);
const USAGE_KEY = "caos_emoji_usage";

const computeFrequent = () => {
  try {
    const stored = JSON.parse(localStorage.getItem(USAGE_KEY) || "{}");
    const sorted = Object.entries(stored).sort((a, b) => b[1] - a[1]).map(([emoji]) => emoji);
    const frequent = sorted.slice(0, 5);
    const remaining = ALL_EMOJIS.filter((emoji) => !frequent.includes(emoji)).slice(0, 2);
    return frequent.length ? [...frequent, ...remaining] : DEFAULT_VISIBLE;
  } catch {
    return DEFAULT_VISIBLE;
  }
};

/**
 * Base44-parity selection menu. Triggered by any text selection inside the target
 * container. Supports 31 emojis with frequency tracking, reply input mode,
 * Read Aloud via browser speechSynthesis, Copy with toast feedback.
 */
export const SelectionReactionPopover = ({ containerRef, onReact, onReply, onCopy, onReadAloud }) => {
  const popoverRef = useRef(null);
  const [position, setPosition] = useState(null);
  const [selectedText, setSelectedText] = useState("");
  const [showAll, setShowAll] = useState(false);
  const [replyMode, setReplyMode] = useState(false);
  const [replyDraft, setReplyDraft] = useState("");
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [visibleEmojis, setVisibleEmojis] = useState(computeFrequent);

  useEffect(() => {
    const host = containerRef?.current;
    if (!host) return undefined;

    const update = () => {
      const selection = window.getSelection();
      if (!selection || selection.isCollapsed) {
        if (!replyMode) { setPosition(null); setSelectedText(""); }
        return;
      }
      const range = selection.getRangeAt(0);
      if (!host.contains(range.commonAncestorContainer)) {
        setPosition(null); setSelectedText("");
        return;
      }
      const text = selection.toString().trim();
      if (!text) { setPosition(null); setSelectedText(""); return; }
      const rect = range.getBoundingClientRect();
      setPosition({
        top: Math.max(8, rect.top - 12 - 220),
        left: Math.min(window.innerWidth - 320, Math.max(8, rect.left + rect.width / 2 - 150)),
      });
      setSelectedText(text);
    };

    const dismiss = (event) => {
      if (popoverRef.current && popoverRef.current.contains(event.target)) return;
      if (replyMode) return;
      update();
    };

    document.addEventListener("selectionchange", update);
    document.addEventListener("mouseup", update);
    document.addEventListener("mousedown", dismiss);
    return () => {
      document.removeEventListener("selectionchange", update);
      document.removeEventListener("mouseup", update);
      document.removeEventListener("mousedown", dismiss);
      if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    };
  }, [containerRef, replyMode]);

  if (!position || !selectedText) return null;

  const trackEmoji = (emoji) => {
    try {
      const stored = JSON.parse(localStorage.getItem(USAGE_KEY) || "{}");
      stored[emoji] = (stored[emoji] || 0) + 1;
      localStorage.setItem(USAGE_KEY, JSON.stringify(stored));
      setVisibleEmojis(computeFrequent());
    } catch { /* noop */ }
  };

  const close = () => {
    window.getSelection()?.removeAllRanges();
    if ("speechSynthesis" in window) window.speechSynthesis.cancel();
    setIsSpeaking(false); setReplyMode(false); setReplyDraft("");
    setPosition(null); setSelectedText(""); setShowAll(false);
  };

  const handleReact = (emoji) => { trackEmoji(emoji); onReact?.(emoji, selectedText); toast.success(`Reacted ${emoji}`); close(); };
  const handleRead = () => {
    if (!("speechSynthesis" in window)) { toast.error("Read aloud unavailable"); return; }
    if (isSpeaking) { window.speechSynthesis.cancel(); setIsSpeaking(false); return; }
    window.getSelection()?.removeAllRanges();
    const utter = new SpeechSynthesisUtterance(selectedText);
    utter.onend = () => setIsSpeaking(false);
    utter.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utter);
    setIsSpeaking(true);
    onReadAloud?.(selectedText);
  };
  const handleCopy = async () => {
    try { await navigator.clipboard.writeText(selectedText); toast.success("Copied to clipboard"); }
    catch { toast.error("Failed to copy"); }
    close();
  };
  const handleReplySubmit = () => {
    if (!replyDraft.trim()) return;
    onReply?.(selectedText, replyDraft.trim());
    toast.success("Reply saved");
    close();
  };

  const emojiRow = showAll ? ALL_EMOJIS : visibleEmojis;

  return (
    <div
      className="selection-reaction-popover"
      data-testid="caos-selection-popover"
      ref={popoverRef}
      style={{ position: "fixed", top: position.top, left: position.left }}
    >
      <div className="selection-reaction-topline" data-testid="caos-selection-popover-topline">
        <span>React or reply</span>
        <button className="selection-reaction-close" data-testid="caos-selection-popover-close" onClick={close} type="button">
          <X size={12} />
        </button>
      </div>
      {!replyMode ? (
        <>
          <div className="selection-reaction-emojis" data-testid="caos-selection-popover-emojis">
            {emojiRow.map((emoji) => (
              <button
                className="selection-reaction-emoji"
                data-testid={`caos-selection-emoji-${emoji}`}
                key={emoji}
                onClick={() => handleReact(emoji)}
                type="button"
              >
                {emoji}
              </button>
            ))}
            <button
              className="selection-reaction-emoji selection-reaction-more"
              data-testid="caos-selection-emoji-more"
              onClick={() => setShowAll((value) => !value)}
              title={showAll ? "Show fewer" : "Show more emojis"}
              type="button"
            >
              <Plus className={showAll ? "selection-reaction-more-open" : ""} size={14} />
            </button>
          </div>
          <div className="selection-reaction-actions" data-testid="caos-selection-popover-actions">
            <button className="selection-reaction-action selection-reaction-action-read" data-testid="caos-selection-read" onClick={handleRead} type="button">
              <Volume2 size={13} />{isSpeaking ? "Stop" : "Read"}
            </button>
            <button className="selection-reaction-action selection-reaction-action-reply" data-testid="caos-selection-reply" onClick={() => setReplyMode(true)} type="button">
              <CornerDownLeft size={13} />Reply
            </button>
            <button className="selection-reaction-action selection-reaction-action-copy" data-testid="caos-selection-copy" onClick={handleCopy} type="button">
              <Copy size={13} />Copy
            </button>
          </div>
        </>
      ) : (
        <div className="selection-reaction-reply">
          <input
            autoFocus
            className="selection-reaction-reply-input"
            data-testid="caos-selection-reply-input"
            onChange={(event) => setReplyDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") handleReplySubmit();
              if (event.key === "Escape") { setReplyMode(false); setReplyDraft(""); }
            }}
            placeholder="Type your reply..."
            value={replyDraft}
          />
          <div className="selection-reaction-reply-actions">
            <button className="selection-reaction-action" data-testid="caos-selection-reply-cancel" onClick={() => { setReplyMode(false); setReplyDraft(""); }} type="button">
              Cancel
            </button>
            <button className="selection-reaction-action selection-reaction-action-send" data-testid="caos-selection-reply-send" onClick={handleReplySubmit} type="button">
              Send
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

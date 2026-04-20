import { useEffect, useRef, useState } from "react";
import { Copy, CornerDownLeft, Volume2 } from "lucide-react";

const EMOJI_SET = ["👍", "❤️", "😂", "🤔", "👀", "🔥", "😊"];

/**
 * Renders a floating popover when the user selects text inside the target container.
 * Popover: emoji reactions + Read Aloud + Reply + Copy on the highlighted fragment.
 */
export const SelectionReactionPopover = ({ containerRef, onReact, onReadAloud, onReply, onCopy }) => {
  const popoverRef = useRef(null);
  const [position, setPosition] = useState(null);
  const [selectedText, setSelectedText] = useState("");

  useEffect(() => {
    const host = containerRef?.current;
    if (!host) return undefined;

    const update = () => {
      const selection = window.getSelection();
      if (!selection || selection.isCollapsed) {
        setPosition(null);
        setSelectedText("");
        return;
      }
      const range = selection.getRangeAt(0);
      if (!host.contains(range.commonAncestorContainer)) {
        setPosition(null);
        setSelectedText("");
        return;
      }
      const text = selection.toString().trim();
      if (!text) {
        setPosition(null);
        setSelectedText("");
        return;
      }
      const rect = range.getBoundingClientRect();
      const hostRect = host.getBoundingClientRect();
      setPosition({
        top: rect.top - hostRect.top - 54,
        left: Math.max(8, rect.left - hostRect.left + rect.width / 2 - 160),
      });
      setSelectedText(text);
    };

    const dismiss = (event) => {
      if (popoverRef.current && popoverRef.current.contains(event.target)) return;
      update();
    };

    document.addEventListener("selectionchange", update);
    document.addEventListener("mouseup", update);
    document.addEventListener("mousedown", dismiss);
    return () => {
      document.removeEventListener("selectionchange", update);
      document.removeEventListener("mouseup", update);
      document.removeEventListener("mousedown", dismiss);
    };
  }, [containerRef]);

  if (!position || !selectedText) return null;

  const handle = (fn) => () => {
    fn?.(selectedText);
    window.getSelection()?.removeAllRanges();
    setPosition(null);
    setSelectedText("");
  };

  return (
    <div
      className="selection-reaction-popover"
      data-testid="caos-selection-popover"
      ref={popoverRef}
      style={{ top: position.top, left: position.left }}
    >
      <div className="selection-reaction-emojis" data-testid="caos-selection-popover-emojis">
        {EMOJI_SET.map((emoji) => (
          <button
            className="selection-reaction-emoji"
            data-testid={`caos-selection-emoji-${emoji}`}
            key={emoji}
            onClick={handle((text) => onReact?.(emoji, text))}
            type="button"
          >
            {emoji}
          </button>
        ))}
      </div>
      <div className="selection-reaction-actions" data-testid="caos-selection-popover-actions">
        <button className="selection-reaction-action" data-testid="caos-selection-read" onClick={handle(onReadAloud)} type="button">
          <Volume2 size={13} />Read
        </button>
        <button className="selection-reaction-action" data-testid="caos-selection-reply" onClick={handle(onReply)} type="button">
          <CornerDownLeft size={13} />Reply
        </button>
        <button className="selection-reaction-action" data-testid="caos-selection-copy" onClick={handle(onCopy)} type="button">
          <Copy size={13} />Copy
        </button>
      </div>
    </div>
  );
};

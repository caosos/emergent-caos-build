import { useMemo } from "react";

const escapeHtml = (text) => String(text || "")
  .replace(/&/g, "&amp;")
  .replace(/</g, "&lt;")
  .replace(/>/g, "&gt;");

const formatInline = (text) => escapeHtml(text)
  .replace(/`([^`]+)`/g, "<code>$1</code>")
  .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");

const parseTableRow = (line) => line.trim().replace(/^\|/, "").replace(/\|$/, "").split("|").map((cell) => formatInline(cell.trim()));
const isTableDivider = (line) => /^\s*\|?(\s*:?-{3,}:?\s*\|)+\s*:?-{3,}:?\s*\|?\s*$/.test(line || "");
const isTableRow = (line) => /^\s*\|.+\|\s*$/.test(line || "");

const renderMarkdown = (md) => {
  if (!md) return "";
  const lines = String(md).split(/\r?\n/);
  const out = [];
  let inCode = false;
  let codeLines = [];
  let listType = null;
  let listItems = [];
  let paragraph = [];

  const flushParagraph = () => {
    if (!paragraph.length) return;
    out.push(`<p>${formatInline(paragraph.join(" "))}</p>`);
    paragraph = [];
  };

  const flushList = () => {
    if (!listType || !listItems.length) return;
    out.push(`<${listType}>${listItems.join("")}</${listType}>`);
    listType = null;
    listItems = [];
  };

  const flushCode = () => {
    if (!codeLines.length) return;
    out.push(`<pre class="admin-docs-code"><code>${escapeHtml(codeLines.join("\n"))}</code></pre>`);
    codeLines = [];
  };

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i];
    const trimmed = line.trim();

    if (trimmed.startsWith("```")) {
      flushParagraph();
      flushList();
      if (inCode) flushCode();
      inCode = !inCode;
      continue;
    }

    if (inCode) {
      codeLines.push(line);
      continue;
    }

    if (isTableRow(line) && isTableDivider(lines[i + 1] || "")) {
      flushParagraph();
      flushList();
      const header = parseTableRow(line);
      const rows = [];
      i += 2;
      while (i < lines.length && isTableRow(lines[i])) {
        rows.push(parseTableRow(lines[i]));
        i += 1;
      }
      i -= 1;
      out.push(
        `<table><thead><tr>${header.map((cell) => `<th>${cell}</th>`).join("")}</tr></thead>`
        + `<tbody>${rows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`).join("")}</tbody></table>`,
      );
      continue;
    }

    if (/^###\s+/.test(trimmed)) {
      flushParagraph();
      flushList();
      out.push(`<h3>${formatInline(trimmed.replace(/^###\s+/, ""))}</h3>`);
      continue;
    }

    if (/^##\s+/.test(trimmed)) {
      flushParagraph();
      flushList();
      out.push(`<h2>${formatInline(trimmed.replace(/^##\s+/, ""))}</h2>`);
      continue;
    }

    if (/^(?:[-*•])\s+/.test(trimmed) || /^\d+\.\s+/.test(trimmed)) {
      flushParagraph();
      const nextType = /^\d+\.\s+/.test(trimmed) ? "ol" : "ul";
      if (listType && listType !== nextType) flushList();
      listType = nextType;
      const itemText = trimmed.replace(/^(?:[-*•]|\d+\.)\s+/, "");
      listItems.push(`<li>${formatInline(itemText)}</li>`);
      continue;
    }

    if (!trimmed) {
      flushParagraph();
      flushList();
      continue;
    }

    paragraph.push(trimmed);
  }

  flushParagraph();
  flushList();
  if (inCode) flushCode();

  return out.join("\n");
};

export const MarkdownMessage = ({ content, testId }) => {
  const rendered = useMemo(() => renderMarkdown(content), [content]);

  return (
    <div
      className="message-markdown admin-docs-markdown"
      dangerouslySetInnerHTML={{ __html: rendered }}
      data-testid={testId}
    />
  );
};

export const WorkingContextStrip = ({ receipt, wcwBudget }) => {
  if (!receipt) return null;

  const items = [
    { key: "arc", label: "ARC", value: `${receipt.active_context_tokens || 0} / ${wcwBudget || 200000}` },
    { key: "sent", label: "Sent", value: receipt.prompt_tokens || 0 },
    { key: "received", label: "Received", value: receipt.completion_tokens || 0 },
    { key: "facts", label: "Facts", value: receipt.personal_facts_count || 0 },
    { key: "global", label: "Global", value: `${receipt.global_cache_count || 0} · ${receipt.global_bin_status || "empty"}` },
  ];

  return (
    <section className="working-context-strip" data-testid="caos-working-context-strip">
      {items.map((item) => (
        <div className="working-context-chip" data-testid={`caos-working-context-${item.key}`} key={item.key}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
        </div>
      ))}
    </section>
  );
};
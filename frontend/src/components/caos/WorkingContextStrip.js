export const WorkingContextStrip = ({ receipt, wcwBudget }) => {
  const activeReceipt = receipt || {
    active_context_tokens: 0,
    prompt_tokens: 0,
    completion_tokens: 0,
    personal_facts_count: 0,
    global_cache_count: 0,
    global_bin_status: "empty",
  };

  const items = [
    { key: "arc", label: "ARC", value: `${activeReceipt.active_context_tokens || 0} / ${wcwBudget || 200000}` },
    { key: "sent", label: "Sent", value: activeReceipt.prompt_tokens || 0 },
    { key: "received", label: "Received", value: activeReceipt.completion_tokens || 0 },
    { key: "facts", label: "Facts", value: activeReceipt.personal_facts_count || 0 },
    { key: "global", label: "Global", value: `${activeReceipt.global_cache_count || 0} · ${activeReceipt.global_bin_status || "empty"}` },
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
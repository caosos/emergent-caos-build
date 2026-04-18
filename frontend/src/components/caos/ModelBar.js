const MODEL_OPTIONS = [
  { label: "Smart Auto", active: true },
  { label: "GPT-5.2", active: true },
  { label: "Gemini 1.5 Pro", active: false },
  { label: "Claude 3.5", active: false },
  { label: "More", active: false },
];


export const ModelBar = () => {
  return (
    <div className="model-bar" data-testid="caos-model-bar">
      {MODEL_OPTIONS.map((option) => (
        <button
          className={`model-chip ${option.active ? "model-chip-active" : "model-chip-disabled"}`}
          data-testid={`caos-model-chip-${option.label.toLowerCase().replace(/[^a-z0-9]+/g, '-')}`}
          key={option.label}
          title={option.active ? option.label : `${option.label} not wired yet`}
          type="button"
        >
          {option.label}
        </button>
      ))}
    </div>
  );
};
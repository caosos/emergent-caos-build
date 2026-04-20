const formatTokens = (value) => {
  const numeric = Number(value) || 0;
  if (numeric >= 1000000) return `${(numeric / 1000000).toFixed(1)}M`;
  if (numeric >= 1000) return `${(numeric / 1000).toFixed(1)}K`;
  return `${numeric}`;
};

const tierClass = (percent) => {
  if (percent > 75) return "thread-mini-meter-fill-red";
  if (percent > 50) return "thread-mini-meter-fill-yellow";
  if (percent > 25) return "thread-mini-meter-fill-blue";
  return "thread-mini-meter-fill-green";
};

/**
 * Compact per-thread WCW meter. Budget defaults to 200K (OpenAI);
 * override to 1M when provider=gemini. Matches Base44 TokenMeter pattern.
 */
export const ThreadMiniMeter = ({ tokens = 0, budget, provider = "openai", isEstimate = false, testId }) => {
  const effectiveBudget = budget || (provider === "gemini" ? 1000000 : 200000);
  const percent = Math.min(100, (tokens / effectiveBudget) * 100);

  return (
    <div className="thread-mini-meter" data-testid={testId || "caos-thread-mini-meter"}>
      <span className="thread-mini-meter-label" data-testid={`${testId || "caos-thread-mini-meter"}-label`}>
        {formatTokens(tokens)} / {formatTokens(effectiveBudget)}{isEstimate ? <span className="thread-mini-meter-est">~</span> : null}
      </span>
      <div className="thread-mini-meter-bar">
        <div className={`thread-mini-meter-fill ${tierClass(percent)}`} style={{ width: `${percent}%` }} />
      </div>
    </div>
  );
};

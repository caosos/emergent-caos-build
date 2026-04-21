/**
 * 5-step onboarding tour modal. Shown on first login (persisted via localStorage flag).
 * Matches Base44 parity: stepper dots, title, body, Skip/Next buttons, final = Get started.
 */
import { useState } from "react";
import { X, ArrowRight, Sparkles, MessageSquare, Brain, Paperclip, Rocket } from "lucide-react";

const STEPS = [
  {
    id: "start",
    icon: <Sparkles size={22} />,
    title: "Start here",
    body: "Type anything — a question, a task, code, a plan. Aria reads it and responds with real intelligence, not canned replies.",
  },
  {
    id: "threads",
    icon: <MessageSquare size={22} />,
    title: "Your threads",
    body: "Every conversation is saved automatically. Switch between threads, search your history, and pick up exactly where you left off.",
  },
  {
    id: "memory",
    icon: <Brain size={22} />,
    title: "Aria remembers",
    body: "Tell Aria to remember something and she will — across every future session. Your preferences, your projects, your context.",
  },
  {
    id: "attach",
    icon: <Paperclip size={22} />,
    title: "Attach anything",
    body: "Drop in files, images, screenshots, or take a photo. Aria can see, read, and reason about everything you share. You can paste images from the clipboard.",
  },
  {
    id: "go",
    icon: <Rocket size={22} />,
    title: "Get started",
    body: "You're ready. Hit Send on anything. Aria starts with a clean slate — tell her what matters, and she remembers.",
  },
];

export const WelcomeTour = ({ isOpen, onClose, onComplete }) => {
  const [index, setIndex] = useState(0);
  if (!isOpen) return null;

  const step = STEPS[index];
  const isLast = index === STEPS.length - 1;

  const handleNext = () => {
    if (isLast) {
      try { localStorage.setItem("caos_tour_completed", "true"); } catch {}
      onComplete?.();
      onClose?.();
    } else {
      setIndex((i) => i + 1);
    }
  };

  const handleSkip = () => {
    try { localStorage.setItem("caos_tour_completed", "true"); } catch {}
    onClose?.();
  };

  return (
    <div className="tour-overlay" data-testid="caos-tour-overlay" onClick={handleSkip}>
      <div
        className="tour-card"
        data-testid="caos-tour-card"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          className="tour-card-close"
          data-testid="caos-tour-close"
          onClick={handleSkip}
          type="button"
          aria-label="close tour"
        >
          <X size={14} />
        </button>

        <div className="tour-dots" data-testid="caos-tour-dots">
          {STEPS.map((s, i) => (
            <span
              key={s.id}
              data-testid={`caos-tour-dot-${i}`}
              className={`tour-dot ${i === index ? "tour-dot-active" : ""} ${i < index ? "tour-dot-done" : ""}`}
            />
          ))}
        </div>

        <div className="tour-icon" data-testid={`caos-tour-icon-${step.id}`}>
          {step.icon}
        </div>

        <h3 className="tour-title" data-testid={`caos-tour-title-${step.id}`}>
          {step.title}
        </h3>

        <p className="tour-body" data-testid={`caos-tour-body-${step.id}`}>
          {step.body}
        </p>

        <div className="tour-actions" data-testid="caos-tour-actions">
          <button
            className="tour-skip-btn"
            data-testid="caos-tour-skip"
            onClick={handleSkip}
            type="button"
          >
            Skip tour
          </button>
          <button
            className="tour-next-btn"
            data-testid={isLast ? "caos-tour-get-started" : "caos-tour-next"}
            onClick={handleNext}
            type="button"
          >
            <span>{isLast ? "Get started" : "Next"}</span>
            <ArrowRight size={14} />
          </button>
        </div>
      </div>
    </div>
  );
};

import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Clapperboard, GitBranch, ImagePlus, MessagesSquare } from "lucide-react";


const FEATURE_SETS = [
  [
    { id: "image", title: "Create Image", description: "Generate stunning AI images", icon: ImagePlus },
    { id: "video", title: "Create Video", description: "Make videos with AI", icon: Clapperboard },
    { id: "mindmap", title: "Create Mindmap", description: "Visualize ideas and concepts", icon: GitBranch },
    { id: "models", title: "Chat with Multiple Models", description: "Compare answers side by side", icon: MessagesSquare },
  ],
  [
    { id: "research", title: "Search Anything", description: "Find answers with context-aware search", icon: MessagesSquare },
    { id: "analyze", title: "Analyze Data", description: "Pull insights from files and receipts", icon: GitBranch },
    { id: "create", title: "Generate Content", description: "Draft fast with memory-aware prompting", icon: Clapperboard },
    { id: "design", title: "Create & Design", description: "Work across media without leaving CAOS", icon: ImagePlus },
  ],
];


export const WelcomeHero = ({ onCardAction }) => {
  const [page, setPage] = useState(0);
  const cards = useMemo(() => FEATURE_SETS[page] || FEATURE_SETS[0], [page]);

  return (
    <section className="welcome-hero" data-testid="caos-welcome-hero">
      <div className="welcome-hero-copy" data-testid="caos-welcome-copy">
        <h1 data-testid="caos-welcome-title">Welcome to CAOS</h1>
        <p data-testid="caos-welcome-subtitle">Search the web, analyze data, generate content, and get instant answers.</p>
        <span className="welcome-hero-kicker" data-testid="caos-welcome-kicker">Try these to see what&apos;s possible</span>
      </div>

      <div className="welcome-carousel-shell" data-testid="caos-welcome-carousel-shell">
        <button
          className="welcome-carousel-arrow"
          data-testid="caos-welcome-prev-button"
          onClick={() => setPage((value) => (value === 0 ? FEATURE_SETS.length - 1 : value - 1))}
          type="button"
        >
          <ChevronLeft size={18} />
        </button>

        <div className="welcome-card-row" data-testid="caos-welcome-card-row">
          {cards.map((card) => (
            <button
              className="welcome-card"
              data-testid={`caos-welcome-card-${card.id}`}
              key={card.id}
              onClick={() => onCardAction?.(card.id)}
              type="button"
            >
              <span className="welcome-card-icon" data-testid={`caos-welcome-card-icon-${card.id}`}>
                <card.icon size={22} />
              </span>
              <strong data-testid={`caos-welcome-card-title-${card.id}`}>{card.title}</strong>
              <span data-testid={`caos-welcome-card-description-${card.id}`}>{card.description}</span>
            </button>
          ))}
        </div>

        <button
          className="welcome-carousel-arrow"
          data-testid="caos-welcome-next-button"
          onClick={() => setPage((value) => (value + 1) % FEATURE_SETS.length)}
          type="button"
        >
          <ChevronRight size={18} />
        </button>
      </div>

      <div className="welcome-carousel-dots" data-testid="caos-welcome-dots">
        {FEATURE_SETS.map((_, index) => (
          <button
            className={`welcome-dot ${page === index ? "welcome-dot-active" : ""}`}
            data-testid={`caos-welcome-dot-${index}`}
            key={`dot-${index}`}
            onClick={() => setPage(index)}
            type="button"
          />
        ))}
      </div>
    </section>
  );
};
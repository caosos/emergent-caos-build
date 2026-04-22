/**
 * ConstellationLayer
 * ------------------
 * Subtle, slow-rotating constellations + planets drifting across the star field.
 * Only visible if you're looking for them — lines at opacity 0.18, stars tiny.
 *
 * - Rotates through ~10 real constellations (Orion, Big Dipper, Cassiopeia, Cygnus,
 *   Lyra, Leo, Scorpius, Perseus, Andromeda, Draco). One visible at a time,
 *   cross-fades every 55–95s.
 * - Planets: Mars (red), Jupiter (tan), Venus (bright white), Saturn (ringed),
 *   drift slowly across the sky. Position resets every few minutes.
 * - Purely visual, pointer-events: none, cannot be interacted with.
 *
 * Mounts once inside CaosShell — fixed, full viewport, z-index: 0 (above the
 * ::before star tiles but below all chat content).
 */
import { useEffect, useMemo, useRef, useState } from "react";

// ---------- Constellation catalog ----------
// Star coords are in a local 0..1 grid; we scale them into a target box.
// Lines are pairs of star indices. Keep it authentic-ish, not astronomically perfect.
const CONSTELLATIONS = [
  { name: "Orion", stars: [
      [0.20, 0.15], [0.72, 0.10], [0.36, 0.38], [0.46, 0.40], [0.56, 0.42],
      [0.18, 0.78], [0.78, 0.82], [0.46, 0.56], [0.50, 0.70],
    ], lines: [[0,2],[2,3],[3,4],[4,1],[2,5],[4,6],[3,7],[7,8]] },
  { name: "Ursa Major", stars: [
      [0.08, 0.45], [0.22, 0.60], [0.36, 0.58], [0.48, 0.48],
      [0.62, 0.38], [0.78, 0.30], [0.92, 0.22],
    ], lines: [[0,1],[1,2],[2,3],[3,4],[4,5],[5,6],[0,3]] },
  { name: "Cassiopeia", stars: [
      [0.08, 0.30], [0.28, 0.62], [0.48, 0.35], [0.68, 0.60], [0.90, 0.30],
    ], lines: [[0,1],[1,2],[2,3],[3,4]] },
  { name: "Cygnus", stars: [
      [0.50, 0.08], [0.50, 0.30], [0.50, 0.55], [0.50, 0.88],
      [0.20, 0.40], [0.80, 0.38],
    ], lines: [[0,1],[1,2],[2,3],[4,2],[2,5]] },
  { name: "Lyra", stars: [
      [0.50, 0.12], [0.35, 0.45], [0.62, 0.40], [0.38, 0.78], [0.64, 0.76],
    ], lines: [[0,1],[0,2],[1,3],[2,4],[3,4],[1,2]] },
  { name: "Leo", stars: [
      [0.82, 0.20], [0.70, 0.32], [0.58, 0.40], [0.50, 0.32],
      [0.42, 0.50], [0.20, 0.72], [0.12, 0.55],
    ], lines: [[0,1],[1,2],[2,3],[3,0],[2,4],[4,5],[5,6],[6,4]] },
  { name: "Scorpius", stars: [
      [0.18, 0.18], [0.28, 0.32], [0.36, 0.45], [0.50, 0.55],
      [0.65, 0.60], [0.78, 0.52], [0.88, 0.38], [0.82, 0.22],
    ], lines: [[0,1],[1,2],[2,3],[3,4],[4,5],[5,6],[6,7]] },
  { name: "Perseus", stars: [
      [0.15, 0.30], [0.30, 0.45], [0.48, 0.38], [0.62, 0.55],
      [0.75, 0.45], [0.85, 0.68],
    ], lines: [[0,1],[1,2],[2,3],[3,4],[3,5]] },
  { name: "Andromeda", stars: [
      [0.12, 0.65], [0.30, 0.58], [0.50, 0.50], [0.70, 0.45], [0.88, 0.40],
      [0.48, 0.28], [0.70, 0.22],
    ], lines: [[0,1],[1,2],[2,3],[3,4],[2,5],[3,6]] },
  { name: "Draco", stars: [
      [0.10, 0.80], [0.22, 0.60], [0.40, 0.55], [0.55, 0.35],
      [0.72, 0.25], [0.85, 0.38], [0.92, 0.58],
    ], lines: [[0,1],[1,2],[2,3],[3,4],[4,5],[5,6]] },
];

const PLANETS = [
  { name: "Mars", color: "#ff7a5f", size: 2.6, glow: "rgba(255, 122, 95, 0.35)" },
  { name: "Jupiter", color: "#e8cfa3", size: 3.2, glow: "rgba(232, 207, 163, 0.3)" },
  { name: "Venus", color: "#ffffff", size: 3.6, glow: "rgba(255, 255, 255, 0.5)" },
  { name: "Saturn", color: "#d9bc8a", size: 2.8, glow: "rgba(217, 188, 138, 0.28)", ring: true },
];

const rand = (min, max) => min + Math.random() * (max - min);
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

export const ConstellationLayer = () => {
  const [current, setCurrent] = useState(() => pick(CONSTELLATIONS));
  const [fading, setFading] = useState(false);
  const [placement, setPlacement] = useState(() => ({
    left: rand(6, 58), top: rand(8, 42), size: rand(22, 32), // all in %
  }));
  const [planets, setPlanets] = useState(() => PLANETS.map((p, i) => ({
    ...p, left: rand(8, 92), top: rand(10, 88), driftId: i, tag: Math.random(),
  })));
  const timerRef = useRef(null);

  // Cycle constellation every 55–95s with a cross-fade.
  useEffect(() => {
    const tick = () => {
      setFading(true);
      setTimeout(() => {
        setCurrent((prev) => {
          const candidates = CONSTELLATIONS.filter((c) => c.name !== prev.name);
          return pick(candidates);
        });
        setPlacement({ left: rand(6, 58), top: rand(8, 42), size: rand(22, 32) });
        setFading(false);
      }, 2200);
      timerRef.current = setTimeout(tick, rand(55_000, 95_000));
    };
    timerRef.current = setTimeout(tick, rand(12_000, 25_000));
    return () => clearTimeout(timerRef.current);
  }, []);

  // Re-roll a random planet position every ~3 minutes (drift feel).
  useEffect(() => {
    const rerollOne = () => {
      setPlanets((prev) => prev.map((p, i) => {
        if (i !== Math.floor(Math.random() * prev.length)) return p;
        return { ...p, left: rand(6, 94), top: rand(6, 94), tag: Math.random() };
      }));
    };
    const id = setInterval(rerollOne, 180_000);
    return () => clearInterval(id);
  }, []);

  const viewBoxSize = 1000;
  const stars = useMemo(() => current.stars.map(([x, y]) => ({
    cx: x * viewBoxSize, cy: y * viewBoxSize,
  })), [current]);

  return (
    <div aria-hidden="true" data-testid="caos-constellation-layer" style={{
      position: "fixed", inset: 0, pointerEvents: "none", zIndex: 0, overflow: "hidden",
    }}>
      {/* Constellation */}
      <svg
        style={{
          position: "absolute",
          left: `${placement.left}%`,
          top: `${placement.top}%`,
          width: `${placement.size}vw`,
          height: `${placement.size}vw`,
          maxWidth: 520, maxHeight: 520,
          opacity: fading ? 0 : 0.22,
          transition: "opacity 2.0s ease, left 2s ease, top 2s ease",
          filter: "drop-shadow(0 0 6px rgba(200, 220, 255, 0.25))",
        }}
        viewBox={`0 0 ${viewBoxSize} ${viewBoxSize}`}
        data-testid={`caos-constellation-${current.name.replace(/\s+/g, "-").toLowerCase()}`}
      >
        {current.lines.map(([a, b], idx) => (
          <line
            key={idx}
            x1={stars[a].cx} y1={stars[a].cy}
            x2={stars[b].cx} y2={stars[b].cy}
            stroke="rgba(200, 220, 255, 0.55)" strokeWidth="1.6" strokeLinecap="round"
          />
        ))}
        {stars.map((s, i) => (
          <circle key={i} cx={s.cx} cy={s.cy} r={4} fill="#ffffff" />
        ))}
        <text
          x={viewBoxSize - 10} y={viewBoxSize - 14}
          textAnchor="end"
          fill="rgba(226, 232, 240, 0.55)"
          fontFamily="ui-monospace, Menlo, monospace"
          fontSize="26" letterSpacing="6"
          style={{ textTransform: "uppercase" }}
        >{current.name}</text>
      </svg>

      {/* Planets */}
      {planets.map((p) => (
        <div
          key={p.driftId}
          data-testid={`caos-planet-${p.name.toLowerCase()}`}
          style={{
            position: "absolute",
            left: `${p.left}%`,
            top: `${p.top}%`,
            width: p.size * 3, height: p.size * 3,
            borderRadius: "50%",
            background: p.color,
            boxShadow: `0 0 ${p.size * 4}px ${p.glow}, 0 0 ${p.size * 8}px ${p.glow}`,
            opacity: 0.8,
            transition: "left 60s linear, top 60s linear",
          }}
          title={p.name}
        >
          {p.ring ? (
            <div style={{
              position: "absolute",
              left: "50%", top: "50%",
              width: p.size * 7, height: p.size * 2.2,
              transform: "translate(-50%, -50%) rotate(-18deg)",
              border: "1px solid rgba(217, 188, 138, 0.55)",
              borderRadius: "50%",
              opacity: 0.7,
            }} />
          ) : null}
        </div>
      ))}
    </div>
  );
};

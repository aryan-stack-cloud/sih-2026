import type { SpectrumFrame } from "../store/useStore";

/**
 * The spectrum waterfall - the one thing this page is remembered by.
 *
 * It is the hero because it *is* the argument. Frequency runs across, time runs down, newest at
 * the top, exactly as an SDR waterfall reads. Drawn on top of it is the receiver's aperture: the
 * K bands it can actually hear this instant. The whole project exists because that aperture is
 * narrower than the spectrum, and this is the only view where you can watch signal stream past
 * uncaught rather than be told it does.
 *
 * Four cell states, each a reserved status colour that never doubles as anything else. Colour is
 * never the only cue - the legend carries a glyph and a written label for every state, and the
 * amber "missed" cells are additionally marked with a notch so they survive a colourblind or
 * printed read.
 */

const CELL_W = 22;
const CELL_H = 9;
const GAP = 2; // surface gap between fills, so adjacent cells never bleed together
const AXIS_H = 18;
const APERTURE_H = 13;

export type CellState = "hit" | "missed" | "listened" | "idle" | "falseAlarm";

const FILL: Record<CellState, string> = {
  hit: "var(--intercepted)",
  missed: "var(--missed)",
  falseAlarm: "var(--false-alarm)",
  listened: "var(--listened)",
  idle: "var(--idle)",
};

function classify(
  band: number,
  frame: SpectrumFrame,
): CellState {
  const active = frame.activeBands.includes(band);
  const scanned = frame.scannedBands.includes(band);
  if (frame.falseAlarmBands.includes(band)) return "falseAlarm";
  if (active && frame.detectedBands.includes(band)) return "hit";
  if (active) return "missed";
  if (scanned) return "listened";
  return "idle";
}

export function Waterfall({
  frames,
  bands,
}: {
  frames: SpectrumFrame[];
  bands: number;
}) {
  if (frames.length === 0) {
    return (
      <p className="empty">
        Waiting for the receiver. Start a run to watch the spectrum.
      </p>
    );
  }

  // Newest first, reading downward - the direction a waterfall actually scrolls.
  const rows = [...frames].reverse();
  const width = bands * CELL_W;
  const height = AXIS_H + APERTURE_H + rows.length * CELL_H;
  const newest = rows[0];

  return (
    <figure style={{ margin: 0 }}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        style={{ display: "block", maxHeight: 460 }}
        role="img"
        aria-label={`Spectrum waterfall over ${bands} bands and the last ${rows.length} observed steps. The receiver hears ${newest.scannedBands.length} bands at a time.`}
      >
        {/* band numbers */}
        {Array.from({ length: bands }, (_, b) => (
          <text
            key={`axis-${b}`}
            x={b * CELL_W + CELL_W / 2}
            y={12}
            textAnchor="middle"
            fontFamily="var(--font-mono)"
            fontSize={9}
            fill="var(--ink-faint)"
          >
            {b}
          </text>
        ))}

        {/* the receiver aperture: what it can hear right now */}
        {newest.scannedBands.length > 0 &&
          (() => {
            const sorted = [...newest.scannedBands].sort((a, z) => a - z);
            const start = sorted[0];
            const contiguous = sorted[sorted.length - 1] - start + 1 === sorted.length;
            const x = start * CELL_W;
            const w = (contiguous ? sorted.length : 1) * CELL_W;
            return (
              <g>
                <rect
                  x={x + 1}
                  y={AXIS_H}
                  width={w - 2}
                  height={APERTURE_H - 3}
                  fill="none"
                  stroke="var(--ink)"
                  strokeWidth={1.5}
                  rx={2}
                />
                <text
                  x={x + w / 2}
                  y={AXIS_H + APERTURE_H - 6}
                  textAnchor="middle"
                  fontFamily="var(--font-mono)"
                  fontSize={7.5}
                  letterSpacing="0.08em"
                  fill="var(--ink)"
                >
                  {w > 40 ? "LISTENING" : "▲"}
                </text>
              </g>
            );
          })()}

        {/* the waterfall itself */}
        {rows.map((frame, r) =>
          Array.from({ length: bands }, (_, b) => {
            const state = classify(b, frame);
            const x = b * CELL_W;
            const y = AXIS_H + APERTURE_H + r * CELL_H;
            const fresh = r === 0 && state === "hit";
            return (
              <g key={`${frame.t}-${b}`}>
                <rect
                  className={fresh ? "hit-fresh" : undefined}
                  x={x + GAP / 2}
                  y={y}
                  width={CELL_W - GAP}
                  height={CELL_H - 1}
                  rx={1.5}
                  fill={FILL[state]}
                  opacity={state === "idle" ? 1 : 0.94}
                />
                {/* secondary encoding for the state that matters most: signal we did not hear */}
                {state === "missed" && (
                  <rect
                    x={x + CELL_W / 2 - 1}
                    y={y + 2}
                    width={2}
                    height={CELL_H - 5}
                    fill="var(--ground)"
                    opacity={0.55}
                  />
                )}
              </g>
            );
          }),
        )}
      </svg>

      <figcaption className="legend">
        <span className="legend-item">
          <span className="legend-swatch" style={{ background: "var(--intercepted)" }} />
          Intercepted
        </span>
        <span className="legend-item">
          <span
            className="legend-swatch"
            style={{
              background: "var(--missed)",
              backgroundImage:
                "linear-gradient(90deg, transparent 44%, var(--ground) 44%, var(--ground) 56%, transparent 56%)",
            }}
          />
          Transmitting, not heard
        </span>
        <span className="legend-item">
          <span className="legend-swatch" style={{ background: "var(--listened)" }} />
          Listened, nothing there
        </span>
        <span className="legend-item">
          <span className="legend-swatch" style={{ background: "var(--false-alarm)" }} />
          False alarm
        </span>
        <span className="legend-item mono" style={{ color: "var(--ink-faint)" }}>
          step {newest.t}
        </span>
      </figcaption>
    </figure>
  );
}

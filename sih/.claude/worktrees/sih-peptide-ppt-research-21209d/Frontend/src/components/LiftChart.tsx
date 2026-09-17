import { useState } from "react";

/**
 * Change against the open-loop sweep.
 *
 * WHY THIS FORM. The metrics are on wildly different scales - Pd is a fraction near 0.2, AIT is a
 * count of steps near 2, censored AIT is in the hundreds. Plotting them together on one value
 * axis would be unreadable, and giving them two axes is the single worst thing you can do to a
 * chart. Expressing every metric as *percent change against the same reference* puts them all on
 * one unitless axis where they are genuinely comparable.
 *
 * It also makes the result honest by construction. Change is diverging data, so it gets a zero
 * line and two poles: better reads teal, worse reads rose, and the metric where the learned
 * policy loses is drawn in the same chart at the same scale as the ones where it wins. There is
 * no arrangement of this chart that hides it.
 */

export interface LiftRow {
  /** Plain language, from the reader's side of the screen - not the metric's field name. */
  label: string;
  /** What the number means, for a reader who does not know the metric. */
  gloss: string;
  percent: number;
  value: number;
  reference: number;
  /** Whether a rise is an improvement; latency metrics are inverted. */
  higherIsBetter: boolean;
  format: (v: number) => string;
}

const ROW_H = 38;
const LABEL_W = 210;
const PAD_R = 74;

export function LiftChart({
  rows,
  referenceName,
  width = 820,
}: {
  rows: LiftRow[];
  referenceName: string;
  width?: number;
}) {
  const [hovered, setHovered] = useState<number | null>(null);

  if (rows.length === 0) {
    return <p className="empty">No comparison yet.</p>;
  }

  const plotW = width - LABEL_W - PAD_R;
  const height = rows.length * ROW_H + 26;
  const maxAbs = Math.max(40, ...rows.map((r) => Math.abs(r.percent))) * 1.12;
  const zeroX = LABEL_W + plotW / 2;
  const scale = (pct: number) => (pct / maxAbs) * (plotW / 2);

  return (
    <figure style={{ margin: 0 }}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        width="100%"
        role="img"
        aria-label={`Percent change against the ${referenceName} for ${rows.length} metrics.`}
      >
        {/* zero line - the reference, and the only grid line that carries meaning */}
        <line
          x1={zeroX}
          y1={4}
          x2={zeroX}
          y2={rows.length * ROW_H + 6}
          stroke="var(--rule)"
          strokeWidth={1}
        />
        <text
          x={zeroX}
          y={height - 6}
          textAnchor="middle"
          fontFamily="var(--font-mono)"
          fontSize={9}
          fill="var(--ink-faint)"
          letterSpacing="0.08em"
        >
          {referenceName.toUpperCase()}
        </text>

        {rows.map((row, i) => {
          const improved = row.higherIsBetter ? row.percent > 0 : row.percent < 0;
          const w = scale(row.percent);
          const y = i * ROW_H + 6;
          const barY = y + 8;
          const barH = 13;
          const x = w >= 0 ? zeroX : zeroX + w;
          const isHovered = hovered === i;

          return (
            <g
              key={row.label}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
            >
              {/* hit target larger than the mark */}
              <rect
                x={0}
                y={y}
                width={width}
                height={ROW_H}
                fill={isHovered ? "var(--panel-raised)" : "transparent"}
                opacity={0.5}
              />

              <text
                x={LABEL_W - 14}
                y={barY + 11}
                textAnchor="end"
                fontSize={13}
                fill="var(--ink)"
              >
                {row.label}
              </text>

              <rect
                x={x}
                y={barY}
                width={Math.max(2, Math.abs(w))}
                height={barH}
                rx={3}
                fill={improved ? "var(--better)" : "var(--worse)"}
              />

              {/* direct label - only six bars, so labelling each is information, not clutter */}
              <text
                x={w >= 0 ? zeroX + Math.abs(w) + 8 : zeroX - Math.abs(w) - 8}
                y={barY + 11}
                textAnchor={w >= 0 ? "start" : "end"}
                fontFamily="var(--font-mono)"
                fontSize={12}
                fontWeight={500}
                fill={improved ? "var(--better)" : "var(--worse)"}
              >
                {row.percent > 0 ? "+" : ""}
                {row.percent.toFixed(0)}%
              </text>

              {isHovered && (
                <text
                  x={LABEL_W - 14}
                  y={barY + 25}
                  textAnchor="end"
                  fontFamily="var(--font-mono)"
                  fontSize={10}
                  fill="var(--ink-muted)"
                >
                  {row.format(row.reference)} → {row.format(row.value)}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      <figcaption className="note" style={{ marginTop: 10 }}>
        Hover a bar for the underlying numbers. Bars right of the line are improvements; the one
        pointing left is where the learned scheduler is genuinely worse.
      </figcaption>
    </figure>
  );
}

/** The table view every chart owes a reader who wants the actual figures. */
export function ComparisonTable({
  policies,
  metrics,
}: {
  policies: Record<string, Record<string, number>>;
  metrics: { key: string; label: string; format: (v: number) => string }[];
}) {
  const names = Object.keys(policies);
  return (
    <table className="data">
      <thead>
        <tr>
          <th>Metric</th>
          {names.map((n) => (
            <th key={n}>{n}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {metrics.map((m) => (
          <tr key={m.key}>
            <td>{m.label}</td>
            {names.map((n) => (
              <td key={n}>{m.format(Number(policies[n][m.key] ?? 0))}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

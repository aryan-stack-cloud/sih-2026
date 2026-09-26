import { useState } from "react";
import { policyLabel } from "../lib/policyLabels";

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
 *
 * WHY A COMPRESSED SCALE. A real run regularly produces one metric that swings 5-10x harder than
 * the rest (a high-priority-detection win in the hundreds of percent is common and is not a bug).
 * A linear axis sized to that one bar flattens every other bar to a hairline a few pixels wide -
 * the chart still has the number right, but you cannot SEE five of your six results. Bar length
 * here is signed-sqrt(percent), which keeps sign and order exact and still gives the outlier the
 * longest bar, but stops it from erasing everything beside it. The printed percent is always the
 * true number - the axis is deliberately not 1:1 with it, which is why there is no tick scale
 * drawn on it: reading it is "which bars are bigger", not "how many pixels equal 10%".
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
  /** Count-backed rates need enough observations before receiving a directional verdict. */
  requiresCounts?: boolean;
  counts?: {
    reference: { success: number; total: number };
    value: { success: number; total: number };
  } | null;
}

/** Sign-preserving compression: keeps order and direction exact, just shrinks the spread so one
    outlier metric cannot flatten the rest of the chart to invisibility. */
const compress = (pct: number) => Math.sign(pct) * Math.sqrt(Math.abs(pct));

/** Pooled two-proportion z score; null means there are no usable count denominators. */
function twoProportionZ(row: LiftRow): number | null {
  const counts = row.counts;
  if (!counts) return null;
  const { success: a, total: nA } = counts.reference;
  const { success: b, total: nB } = counts.value;
  if (![a, b, nA, nB].every(Number.isInteger) || nA <= 0 || nB <= 0 ||
      a < 0 || b < 0 || a > nA || b > nB) return null;
  const pooled = (a + b) / (nA + nB);
  const se = Math.sqrt(pooled * (1 - pooled) * (1 / nA + 1 / nB));
  return se > 0 ? (b / nB - a / nA) / se : null;
}

type Verdict = "better" | "worse" | "same" | "uncertain";

function verdictFor(row: LiftRow): Verdict {
  if (row.requiresCounts) {
    const z = twoProportionZ(row);
    if (z === null || Math.abs(z) < 1.96) return "uncertain";
  }
  if (row.percent === 0) return "same";
  return (row.higherIsBetter ? row.percent > 0 : row.percent < 0) ? "better" : "worse";
}

const VERDICT_LABEL: Record<Verdict, string> = {
  better: "▲ better",
  worse: "▼ worse",
  same: "= same",
  uncertain: "≈ too few to call",
};

export function LiftChart({
  rows,
  referenceName,
  policyName,
}: {
  rows: LiftRow[];
  referenceName: string;
  policyName: string;
}) {
  const [hovered, setHovered] = useState<number | null>(null);

  const validRows = rows.filter((r) =>
    Number.isFinite(r.percent) && Number.isFinite(r.value) && Number.isFinite(r.reference),
  );
  if (validRows.length === 0) {
    return <p className="empty">No finite relative lifts are available. Check the underlying values; a zero reference has no percent change.</p>;
  }
  const verdictCounts = validRows.reduce<Record<Verdict, number>>((counts, row) => {
    counts[verdictFor(row)]++;
    return counts;
  }, { better: 0, worse: 0, same: 0, uncertain: 0 });

  const maxAbs = Math.max(compress(20), ...validRows.map((r) => Math.abs(compress(r.percent)))) * 1.15;
  const scale = (pct: number) => (compress(pct) / maxAbs) * 45;
  const rawMax = Math.max(...validRows.map((r) => Math.abs(r.percent)));
  const gridPercents = [25, 50, 100, 200, 400].filter((g) => g <= Math.max(rawMax * 1.1, 30));
  const hoveredRow = hovered !== null ? validRows[hovered] : null;

  return (
    <figure className="lift-chart">
      <div className="lift-takeaway">
        <strong>{policyName} beats the {referenceName} on {verdictCounts.better} of {validRows.length} measures</strong>
        <span className="lift-takeaway-counts">
          <span className="lift-verdict lift-verdict--better">▲ {verdictCounts.better} better</span>
          <span className="lift-verdict lift-verdict--worse">▼ {verdictCounts.worse} worse</span>
          {verdictCounts.uncertain > 0 && <span className="lift-verdict lift-verdict--uncertain">≈ {verdictCounts.uncertain} too few to call</span>}
          {verdictCounts.same > 0 && <span className="lift-verdict lift-verdict--same">= {verdictCounts.same} same</span>}
        </span>
      </div>
      <div className="lift-rows" role="list" aria-label={`Percent change against ${referenceName}`}>
        {validRows.map((row, i) => {
          const verdict = verdictFor(row);
          const bar = scale(row.percent);
          const counts = row.counts;
          const referenceValue = counts
            ? `${counts.reference.success} / ${counts.reference.total}` : row.format(row.reference);
          const policyValue = counts
            ? `${counts.value.success} / ${counts.value.total}` : row.format(row.value);
          return (
            <div
              className="lift-row"
              key={row.label}
              role="listitem"
              tabIndex={0}
              aria-label={`${row.label}: ${referenceValue} to ${policyValue}; ${row.percent > 0 ? "+" : ""}${row.percent.toFixed(0)} percent; ${VERDICT_LABEL[verdict]}. ${row.gloss}`}
              onMouseEnter={() => setHovered(i)}
              onMouseLeave={() => setHovered(null)}
              onFocus={() => setHovered(i)}
              onBlur={() => setHovered(null)}
            >
              <span className="lift-label">{row.label}</span>
              <svg className="lift-plot" viewBox="0 0 100 24" preserveAspectRatio="none" aria-hidden="true">
                {gridPercents.flatMap((g) => [g, -g].map((signed) => (
                  <line key={signed} x1={50 + scale(signed)} x2={50 + scale(signed)} y1={2} y2={22} stroke="var(--rule)" strokeWidth={0.25} />
                )))}
                <line x1={50} x2={50} y1={0} y2={24} stroke="var(--ink-faint)" strokeWidth={0.35} />
                <rect
                  x={bar < 0 ? 50 + bar : 50}
                  y={7}
                  width={Math.max(0.8, Math.abs(bar))}
                  height={10}
                  rx={0.6}
                  fill={verdict === "better" ? "var(--better)" : verdict === "worse" ? "var(--worse)" : "var(--ink-faint)"}
                />
              </svg>
              <span className="lift-figures">
                <span className="lift-reference">{referenceValue}{counts && <small>{row.format(row.reference)}</small>}</span>
                <span className="lift-arrow" aria-hidden="true">→</span>
                <strong className="lift-policy-value">{policyValue}{counts && <small>{row.format(row.value)}</small>}</strong>
              </span>
              <span className="lift-outcome">
                <span className="lift-percent">{row.percent > 0 ? "+" : ""}{row.percent.toFixed(0)}%</span>
                <span className={`lift-verdict lift-verdict--${verdict}`}>{VERDICT_LABEL[verdict]}</span>
              </span>
            </div>
          );
        })}
      </div>

      <div className="lift-detail" aria-live="polite">
        {hoveredRow ? (
          <>
            <strong>{hoveredRow.label}.</strong> {hoveredRow.gloss}.
          </>
        ) : (
          <span className="lift-detail-placeholder">
            Hover or focus a row for what it measures.
          </span>
        )}
      </div>

      <figcaption className="note" style={{ marginTop: 10 }}>
        Lower is better for reaction time, all bursts. “Too few to call” means the count difference
        did not clear a 95% two-proportion check. Bar length is compressed so one large swing does
        not flatten the rest; the printed percent is exact.
      </figcaption>
    </figure>
  );
}

/** The table view every chart owes a reader who wants the actual figures. */
export function ComparisonTable({
  policies,
  metrics,
}: {
  policies: Record<string, Record<string, unknown>>;
  metrics: { key: string; label: string; format: (v: number) => string }[];
}) {
  const names = Object.keys(policies);
  return (
    <table className="data metric-table">
      <thead>
        <tr>
          <th>Metric</th>
          {names.map((n) => (
            <th key={n}>{policyLabel(n)}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {metrics.map((m) => (
          <tr key={m.key}>
            <td>{m.label}</td>
            {names.map((n) => (
              <td key={n}>{typeof policies[n]?.[m.key] === "number" && Number.isFinite(policies[n][m.key])
                ? m.format(policies[n][m.key] as number) : "—"}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}

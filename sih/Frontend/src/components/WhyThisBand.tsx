import type { WsFrame } from "../types/contract";

/**
 * The explainability the judge view promised: why the scheduler is listening where it is.
 *
 * Index decisions decompose into named terms, which render as bars; every other policy scores
 * from learned weights with nothing to decompose, so those decisions say so and still show
 * the reward line. The window derives from the decision's start band plus K, wrapping past
 * the top band back to 01 the way the receiver's aperture does.
 */

const SOURCE_CHIP: Record<string, string> = {
  floor: "Search: random floor keeps sampling where little is known",
  index: "Priority: highest score this step",
  deadline: "Coverage: this band had waited too long",
};

const TERM_LABELS: Record<string, string> = {
  value: "Expected catch",
  information: "Information gain",
  deadline: "Waiting too long",
  novelty: "Novelty",
};

const REWARD_LABELS: Record<string, string> = {
  D: "detection",
  P: "priority",
  L: "delay",
  F: "false alarm",
  C: "repeat look",
  M: "missed threat",
};

const pad2 = (band: number) => String(band + 1).padStart(2, "0");

/** The K-band window from this step: scanned bands when present, else action plus K. */
function windowBands(decision: WsFrame, bands: number, k: number): number[] {
  if (bands <= 0 || k <= 0) return [];
  const scanned = decision.scanned_bands?.filter(
    (band): band is number =>
      Number.isInteger(band) && (band as number) >= 0 && (band as number) < bands,
  );
  if (scanned && scanned.length > 0) return scanned.slice(0, k);
  if (
    typeof decision.action === "number" &&
    Number.isInteger(decision.action) &&
    decision.action >= 0 &&
    decision.action < bands
  ) {
    return Array.from({ length: k }, (_, i) => (decision.action as number) + i)
      .map((band) => band % bands);
  }
  return [];
}

function formatTerm(raw: unknown): string {
  const value = Number(raw);
  return Number.isFinite(value) ? value.toFixed(2) : String(raw);
}

function rewardLine(decision: WsFrame): string | null {
  const terms = decision.reward_terms
    ? Object.entries(decision.reward_terms).map(([key, raw]) => {
      const label = REWARD_LABELS[key];
      return label === undefined ? `${key} ${formatTerm(raw)}` : `${key} ${label} ${formatTerm(raw)}`;
    })
    : [];
  const head =
    typeof decision.reward === "number" && Number.isFinite(decision.reward)
      ? `Reward ${decision.reward.toFixed(2)}`
      : null;
  if (head && terms.length > 0) return `${head} (${terms.join(" · ")})`;
  return head ?? (terms.length > 0 ? terms.join(" · ") : null);
}

export function WhyThisBand({
  decision,
  bands,
  policyLabel,
  k = 2,
}: {
  decision: WsFrame | null;
  bands: number;
  policyLabel: string;
  k?: number;
}) {
  if (!decision) {
    return (
      <section className="panel judge-panel" aria-label={`Why this band for ${policyLabel}`}>
        <div className="judge-head">
          <h3 className="judge-title">Why this band?</h3>
          <span className="judge-policy">{policyLabel}</span>
        </div>
        <p className="judge-note">Waiting for the first decision.</p>
      </section>
    );
  }

  const window = windowBands(decision, bands, k);
  const chip = decision.decision_source
    ? SOURCE_CHIP[decision.decision_source]
    : undefined;
  const breakdown = decision.index_breakdown;
  const hasBreakdown = !!breakdown && Object.keys(breakdown).length > 0;
  const reward = rewardLine(decision);

  const shown = hasBreakdown
    ? ["value", "information", "deadline"]
      .map((key) => ({ key, label: TERM_LABELS[key], value: breakdown[key] ?? 0 }))
      .concat(
        (breakdown["novelty"] ?? 0) !== 0
          ? [{ key: "novelty", label: TERM_LABELS["novelty"], value: breakdown["novelty"] ?? 0 }]
          : [],
      )
    : [];
  const peak = Math.max(0, ...shown.map((term) => term.value));

  return (
    <section className="panel judge-panel" aria-label={`Why this band for ${policyLabel}`}>
      <div className="judge-head">
        <h3 className="judge-title">Why this band?</h3>
        <span className="judge-policy">{policyLabel}</span>
      </div>
      <p className="judge-window">
        {window.length > 0
          ? `Listening to bands ${window.map(pad2).join("-")} of ${bands}`
          : "Listening window unknown."}
      </p>
      {chip && (
        <p>
          <span className="judge-chip">{chip}</span>
        </p>
      )}
      {hasBreakdown ? (
        peak === 0 ? (
          <p className="judge-note">All terms scored zero this step.</p>
        ) : (
          <div className="judge-terms">
            {shown.map((term) => (
              <div key={term.key} className="judge-term">
                <span className="judge-term-label">{term.label}</span>
                <span className="judge-term-bar">
                  <i style={{ width: `${(Math.max(term.value, 0) / peak) * 100}%` }} />
                </span>
                <span className="judge-term-value mono">{term.value.toFixed(2)}</span>
              </div>
            ))}
          </div>
        )
      ) : (
        <p className="judge-note">
          This policy scores bands from learned weights and does not expose
          per-term scores.
        </p>
      )}
      {reward ? (
        <p className="judge-reward">{reward}</p>
      ) : (
        <p className="judge-note">No reward reported this step.</p>
      )}
    </section>
  );
}

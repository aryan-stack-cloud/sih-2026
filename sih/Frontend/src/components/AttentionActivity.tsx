import { attentionShares, matchScore } from "../lib/attention";
import type { PerBandCounters } from "../types/contract";

/**
 * Whether listening time is going where the signals are, derived client-side from the
 * counters already inside the live snapshot - no backend change needed for this panel.
 *
 * The diverging chart reads like the wireframe's attention strip: activity share rises above
 * the axis, look share hangs below it. Activity uses --electric because the --missed amber is
 * reserved for missed transmissions in the waterfall, and reusing it here would claim a miss
 * on bands nobody failed to hear.
 */

const pad2 = (band: number) => String(band + 1).padStart(2, "0");

export function AttentionActivity({
  perBand,
  bands,
  policyLabel,
}: {
  perBand?: PerBandCounters;
  bands: number;
  policyLabel: string;
}) {
  const heard = perBand?.heard?.reduce((sum, count) => sum + count, 0) ?? 0;
  const shares = perBand ? attentionShares(perBand) : null;
  const empty =
    !perBand ||
    !shares ||
    shares.total.looks + shares.total.active + heard === 0;

  if (empty) {
    return (
      <section className="panel judge-panel">
        <h3 className="judge-title">Attention vs activity</h3>
        <p className="judge-note">Waiting for the run to start.</p>
      </section>
    );
  }

  const score = matchScore(perBand);
  const percent = Math.round(score * 100);
  const peak = Math.max(0, ...shares.looks, ...shares.active);

  return (
    <section className="panel judge-panel">
      <h3 className="judge-title">Attention vs activity</h3>
      <p className="judge-note">
        Up is the share of transmissions on each band, down is the share of{" "}
        {policyLabel} listening time.
      </p>
      <p className="judge-match">
        <strong>{percent}%</strong> of listening time followed the activity
      </p>
      <div
        className="judge-diverge"
        role="img"
        aria-label={`Attention versus activity for ${policyLabel}: match ${percent}%.`}
      >
        {Array.from({ length: bands }, (_, band) => {
          const up = peak === 0 ? 0 : ((shares.active[band] ?? 0) / peak) * 100;
          const down = peak === 0 ? 0 : ((shares.looks[band] ?? 0) / peak) * 100;
          return (
            <div key={band} className="judge-band">
              <span className="judge-track judge-track-up">
                <i className="judge-activity" style={{ height: `${up}%` }} />
              </span>
              <span className="judge-axis" aria-hidden="true" />
              <span className="judge-track judge-track-down">
                <i className="judge-looks" style={{ height: `${down}%` }} />
              </span>
              <small className="judge-band-label">{pad2(band)}</small>
            </div>
          );
        })}
      </div>
      <div className="judge-visually-hidden">
        <table>
          <caption>
            Per-band listening and transmission counts for {policyLabel}
          </caption>
          <thead>
            <tr>
              <th scope="col">Band</th>
              <th scope="col">Looks</th>
              <th scope="col">Active</th>
              <th scope="col">Heard</th>
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: bands }, (_, band) => (
              <tr key={band}>
                <th scope="row">{pad2(band)}</th>
                <td>{perBand.looks?.[band] ?? 0}</td>
                <td>{perBand.active?.[band] ?? 0}</td>
                <td>{perBand.heard?.[band] ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

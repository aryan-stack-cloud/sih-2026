import { Waterfall } from "./Waterfall";
import { useRunWatcher } from "../hooks/useRunWatcher";
import { liveReadouts } from "../lib/liveReadouts";
import { alignFrames } from "../lib/raceAlign";
import type { SpectrumFrame } from "../lib/frameWindow";
import type { LiveSnapshot } from "../types/contract";

/**
 * The head-to-head race: the learned scheduler against the fixed sweep on the identical
 * spectrum. Both simulations are created with the same seed, so the transmissions are the
 * same and only where each receiver listens differs; rows are matched by step, with the run
 * that is ahead trimmed to the slower one's progress.
 *
 * The challenger reuses the store's single socket (its frames and live snapshot arrive as
 * props); only the reference run opens its own socket, through `useRunWatcher`.
 */

const pct = (v: number) => `${(v * 100).toFixed(1)}%`;

function Readouts({ live }: { live: LiveSnapshot | null }) {
  // Final metrics once the run ends, otherwise derived from the cumulative per-band
  // counters so the columns read live instead of showing "—" for most of the run.
  const readouts = liveReadouts(live);
  return (
    <div className="race-readouts">
      <span className="race-readout">
        <b>{readouts.pd !== null ? pct(readouts.pd) : "—"}</b>
        <small>spectrum heard</small>
      </span>
      <span className="race-readout">
        <b>{live ? live.counters.detections.toLocaleString() : "—"}</b>
        <small>interceptions</small>
      </span>
      <span className="race-readout">
        <b>{readouts.scanEfficiency !== null ? pct(readouts.scanEfficiency) : "—"}</b>
        <small>listening efficiency</small>
      </span>
    </div>
  );
}

function Lane({
  label,
  frames,
  live,
  bands,
}: {
  label: string;
  frames: SpectrumFrame[];
  live: LiveSnapshot | null;
  bands: number;
}) {
  return (
    <div className="race-lane" role="group" aria-label={label}>
      <div className="race-lane-head">
        <strong>{label}</strong>
        <span className="mono">step {live ? live.t : "—"}</span>
      </div>
      <Readouts live={live} />
      <Waterfall frames={frames} bands={bands} />
    </div>
  );
}

export function RacePanel({
  bands,
  reference,
  challenger,
  note,
}: {
  bands: number;
  reference: { label: string; simulationId: string | null };
  challenger: { label: string; frames: SpectrumFrame[]; live: LiveSnapshot | null };
  note?: string;
}) {
  const watched = useRunWatcher(reference.simulationId);

  // A note means the reference run never materialised: say so and show only the run we have.
  if (note) {
    return (
      <div>
        <p className="note" role="status">{note}</p>
        <div className="race-grid">
          <Lane label={challenger.label} frames={challenger.frames} live={challenger.live} bands={bands} />
        </div>
      </div>
    );
  }

  const [challengerFrames, referenceFrames] = alignFrames(challenger.frames, watched.frames);

  return (
    <div>
      <div className="race-grid">
        <Lane label={reference.label} frames={referenceFrames} live={watched.live} bands={bands} />
        <Lane label={challenger.label} frames={challengerFrames} live={challenger.live} bands={bands} />
      </div>
      <p className="note">
        Both columns show the same transmissions (same seed); rows are matched by step.
      </p>
    </div>
  );
}

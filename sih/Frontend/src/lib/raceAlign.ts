/**
 * Step alignment for the race view (no runtime imports).
 *
 * <p>The two race runs stream independently, so one is always ahead: filtering both frame
 * lists to the `t` values present in BOTH trims the faster run to the slower one's progress.
 * Each list keeps its own arrival order, and both are capped to the newest shared window.
 *
 * <p>When the runs share no step yet (one side is still empty or the streams have not
 * overlapped), the inputs come back unchanged so each column keeps showing its own frames
 * instead of going blank. This module must stay import-free at runtime: the `node --test`
 * suite imports it with an explicit `.ts` extension under type stripping, so only
 * `import type` and erasable TypeScript are allowed.
 */

import type { SpectrumFrame } from "./frameWindow";

/** Newest shared steps kept per column; matches the store's own frame tail. */
export const RACE_WINDOW = 40;

/**
 * Restricts both frame lists to the newest `RACE_WINDOW` `t` values present in BOTH,
 * preserving each list's own arrival order.
 */
export function alignFrames(
  challengerFrames: SpectrumFrame[],
  referenceFrames: SpectrumFrame[],
): [SpectrumFrame[], SpectrumFrame[]] {
  const referenceSteps = new Set(referenceFrames.map((frame) => frame.t));
  const sharedChallenger = challengerFrames.filter((frame) => referenceSteps.has(frame.t));
  // No overlap yet: each column keeps its own frames (including two empty lists).
  if (sharedChallenger.length === 0) return [challengerFrames, referenceFrames];
  // The window is chosen first, by numerically largest shared `t`, so both sides cover
  // the same steps even when the two streams arrive in different orders; slicing each
  // side afterwards would keep different steps per side.
  const windowSteps = new Set(
    [...new Set(sharedChallenger.map((frame) => frame.t))]
      .sort((a, b) => a - b)
      .slice(-RACE_WINDOW),
  );
  return [
    challengerFrames.filter((frame) => windowSteps.has(frame.t)),
    referenceFrames.filter((frame) => windowSteps.has(frame.t)),
  ];
}

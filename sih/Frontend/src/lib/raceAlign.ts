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
 * Restricts both frame lists to the `t` values present in BOTH, preserving each list's own
 * order and keeping at most the last `RACE_WINDOW` shared steps per side.
 */
export function alignFrames(
  challengerFrames: SpectrumFrame[],
  referenceFrames: SpectrumFrame[],
): [SpectrumFrame[], SpectrumFrame[]] {
  const referenceSteps = new Set(referenceFrames.map((frame) => frame.t));
  const sharedChallenger = challengerFrames.filter((frame) => referenceSteps.has(frame.t));
  // No overlap yet: each column keeps its own frames (including two empty lists).
  if (sharedChallenger.length === 0) return [challengerFrames, referenceFrames];
  const sharedSteps = new Set(sharedChallenger.map((frame) => frame.t));
  const sharedReference = referenceFrames.filter((frame) => sharedSteps.has(frame.t));
  return [sharedChallenger.slice(-RACE_WINDOW), sharedReference.slice(-RACE_WINDOW)];
}

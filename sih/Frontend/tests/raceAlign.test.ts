import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { RACE_WINDOW, alignFrames } from "../src/lib/raceAlign.ts";
import type { SpectrumFrame } from "../src/lib/frameWindow.ts";

function frame(t: number): SpectrumFrame {
  return {
    t,
    activeBands: [t % 4],
    scannedBands: [0, 1],
    detectedBands: [],
    falseAlarmBands: [],
  };
}

function frames(...steps: number[]): SpectrumFrame[] {
  return steps.map(frame);
}

describe("alignFrames", () => {
  it("keeps only the t values present in both runs", () => {
    const [challenger, reference] = alignFrames(
      frames(1, 2, 3, 4),
      frames(2, 3, 5),
    );
    assert.deepEqual(challenger.map((f) => f.t), [2, 3]);
    assert.deepEqual(reference.map((f) => f.t), [2, 3]);
  });

  it("preserves each run's own order", () => {
    const [challenger, reference] = alignFrames(
      frames(5, 3, 1, 4),
      frames(4, 1, 3, 5),
    );
    assert.deepEqual(challenger.map((f) => f.t), [5, 3, 1, 4]);
    assert.deepEqual(reference.map((f) => f.t), [4, 1, 3, 5]);
  });

  it("trims the run that is ahead to the slower run's progress", () => {
    const [challenger, reference] = alignFrames(
      frames(1, 2, 3, 4, 5, 6),
      frames(1, 2, 3),
    );
    assert.deepEqual(challenger.map((f) => f.t), [1, 2, 3]);
    assert.deepEqual(reference.map((f) => f.t), [1, 2, 3]);
  });

  it("caps the window at the 40 newest shared steps", () => {
    assert.equal(RACE_WINDOW, 40);
    const steps = Array.from({ length: 60 }, (_, i) => i);
    const [challenger, reference] = alignFrames(frames(...steps), frames(...steps));
    assert.equal(challenger.length, 40);
    assert.equal(reference.length, 40);
    assert.deepEqual(challenger.map((f) => f.t), steps.slice(-40));
    assert.deepEqual(reference.map((f) => f.t), steps.slice(-40));
  });

  it("returns the inputs unchanged when the runs share no step", () => {
    const challenger = frames(1, 2, 3);
    const reference = frames(4, 5, 6);
    const [keptChallenger, keptReference] = alignFrames(challenger, reference);
    assert.deepEqual(keptChallenger.map((f) => f.t), [1, 2, 3]);
    assert.deepEqual(keptReference.map((f) => f.t), [4, 5, 6]);
    // One-sided empties are disjoint too: the run with frames keeps them while the
    // other run has not produced its first frame yet.
    assert.deepEqual(alignFrames(frames(1, 2), []), [frames(1, 2), []]);
  });

  it("returns empty arrays for empty inputs", () => {
    assert.deepEqual(alignFrames([], []), [[], []]);
  });
});

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { liveReadouts } from "../src/lib/liveReadouts.ts";

describe("liveReadouts", () => {
  it("derives pd and scanEfficiency from per_band", () => {
    const readouts = liveReadouts({
      per_band: { looks: [10, 20], active: [4, 6], heard: [1, 4], useful: [5, 15] },
    });
    assert.equal(readouts.pd, 0.5);
    assert.equal(readouts.scanEfficiency, 20 / 30);
  });

  it("prefers the final metrics over per_band when both exist", () => {
    const readouts = liveReadouts({
      metrics: { pd: 0.75, scan_efficiency: 0.25 },
      per_band: { looks: [10, 20], active: [4, 6], heard: [1, 4], useful: [5, 15] },
    });
    assert.equal(readouts.pd, 0.75);
    assert.equal(readouts.scanEfficiency, 0.25);
  });

  it("gives null for a zero denominator", () => {
    // No active transmissions yet: pd has nothing to divide by.
    assert.deepEqual(
      liveReadouts({ per_band: { looks: [3], active: [0], heard: [0], useful: [1] } }),
      { pd: null, scanEfficiency: 1 / 3 },
    );
    // No looks yet: efficiency has nothing to divide by.
    assert.deepEqual(
      liveReadouts({ per_band: { looks: [0, 0], active: [2, 2], heard: [1, 1] } }),
      { pd: 0.5, scanEfficiency: null },
    );
  });

  it("derives pd while efficiency is null when useful is missing", () => {
    // Older Backends omit useful: pd still resolves, efficiency cannot.
    const readouts = liveReadouts({
      per_band: { looks: [10], active: [4], heard: [3] },
    });
    assert.equal(readouts.pd, 0.75);
    assert.equal(readouts.scanEfficiency, null);
  });

  it("gives null for the field whose array holds a non-finite entry", () => {
    const readouts = liveReadouts({
      per_band: { looks: [10, 20], active: [4, Number.NaN], heard: [1, 4], useful: [5, 15] },
    });
    assert.equal(readouts.pd, null);
    assert.equal(readouts.scanEfficiency, 20 / 30);
  });

  it("gives both null for null, undefined or empty live", () => {
    assert.deepEqual(liveReadouts(null), { pd: null, scanEfficiency: null });
    assert.deepEqual(liveReadouts(undefined), { pd: null, scanEfficiency: null });
    assert.deepEqual(liveReadouts({}), { pd: null, scanEfficiency: null });
  });

  it("falls back to the derived value when a metrics value is NaN", () => {
    const readouts = liveReadouts({
      metrics: { pd: Number.NaN, scan_efficiency: 0.25 },
      per_band: { looks: [10, 20], active: [4, 6], heard: [1, 4], useful: [5, 15] },
    });
    assert.equal(readouts.pd, 0.5);
    assert.equal(readouts.scanEfficiency, 0.25);
  });

  it("uses metrics alone when per_band is missing", () => {
    const readouts = liveReadouts({
      metrics: { pd: 0.6, scan_efficiency: 0.4 },
    });
    assert.equal(readouts.pd, 0.6);
    assert.equal(readouts.scanEfficiency, 0.4);
  });
});

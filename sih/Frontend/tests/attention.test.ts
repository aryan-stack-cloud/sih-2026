import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { attentionShares, matchScore } from "../src/lib/attention.ts";
import type { PerBandCounters } from "../src/types/contract.ts";

function counters(
  looks: number[],
  active: number[],
  heard?: number[],
): PerBandCounters {
  return {
    looks,
    active,
    heard: heard ?? looks.map(() => 0),
  };
}

describe("attentionShares", () => {
  it("normalises each array to sum to 1", () => {
    const shares = attentionShares(counters([3, 1, 0, 0], [1, 1, 1, 1]));
    assert.deepEqual(shares.looks, [0.75, 0.25, 0, 0]);
    assert.deepEqual(shares.active, [0.25, 0.25, 0.25, 0.25]);
    assert.deepEqual(shares.total, { looks: 4, active: 4 });
  });

  it("gives all-zero shares when the totals are zero", () => {
    const shares = attentionShares(counters([0, 0], [0, 0], [0, 0]));
    assert.deepEqual(shares.looks, [0, 0]);
    assert.deepEqual(shares.active, [0, 0]);
    assert.deepEqual(shares.total, { looks: 0, active: 0 });
    assert.equal(matchScore(counters([0, 0], [0, 0], [0, 0])), 0);
  });

  it("scores 0 when either total is zero", () => {
    assert.equal(matchScore(counters([0, 0], [1, 1])), 0);
    assert.equal(matchScore(counters([1, 1], [0, 0])), 0);
  });
});

describe("matchScore", () => {
  it("scores identical distributions as 1", () => {
    // Same shape up to a scale factor: shares coincide, so every min is the
    // share itself and the sum is 1.
    const score = matchScore(counters([1, 2, 3], [2, 4, 6]));
    assert.ok(Math.abs(score - 1) < 1e-12, `expected ~1, got ${score}`);
  });

  it("scores disjoint distributions as 0", () => {
    assert.equal(matchScore(counters([5, 5, 0, 0], [0, 0, 5, 5])), 0);
  });

  it("computes a known 4-band example by hand", () => {
    // looks [3,1,0,0] total 4 -> shares [.75,.25,0,0]; active [1,1,1,1]
    // total 4 -> shares [.25,.25,.25,.25]; score = min(.75,.25) +
    // min(.25,.25) + min(0,.25) + min(0,.25) = .25 + .25 + 0 + 0 = .5.
    assert.equal(matchScore(counters([3, 1, 0, 0], [1, 1, 1, 1])), 0.5);
  });

  it("ignores heard", () => {
    const base = counters([3, 1, 0, 0], [1, 1, 1, 1], [0, 0, 0, 0]);
    const loud = counters([3, 1, 0, 0], [1, 1, 1, 1], [97, 42, 13, 8]);
    assert.equal(matchScore(base), matchScore(loud));
  });
});

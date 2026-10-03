import { describe, it } from "node:test";
import assert from "node:assert/strict";
import { waitForRunsToFinish } from "../src/lib/raceFinish.ts";

/** Injectable clock: sleep advances `now`, so no test ever waits on a real timer. */
function fakeClock() {
  const state = { now: 0, sleeps: 0 };
  return {
    state,
    now: () => state.now,
    sleep: async (ms: number) => {
      state.sleeps++;
      state.now += ms;
    },
  };
}

describe("waitForRunsToFinish", () => {
  it("returns finished at once when nothing is running, without sleeping", async () => {
    const clock = fakeClock();
    let polls = 0;
    const result = await waitForRunsToFinish(["a", "b"], {
      isRunning: async () => {
        polls++;
        return false;
      },
      sleep: clock.sleep,
      now: clock.now,
    });
    assert.equal(result, "finished");
    assert.equal(polls, 2);
    assert.equal(clock.state.sleeps, 0);
  });

  it("polls until a run stops, then returns finished", async () => {
    const clock = fakeClock();
    let polls = 0;
    const result = await waitForRunsToFinish(["a"], {
      isRunning: async () => (++polls < 3),
      sleep: clock.sleep,
      now: clock.now,
    });
    assert.equal(result, "finished");
    assert.equal(polls, 3);
    assert.equal(clock.state.sleeps, 2);
  });

  it("returns capped after a bounded number of polls when a run never stops", async () => {
    const clock = fakeClock();
    let polls = 0;
    const result = await waitForRunsToFinish(["a"], {
      isRunning: async () => {
        polls++;
        return true;
      },
      sleep: clock.sleep,
      now: clock.now,
      intervalMs: 500,
      capMs: 2000,
    });
    assert.equal(result, "capped");
    // Bounded: one poll per interval plus the final deadline poll, never a spin.
    assert.ok(polls <= 2000 / 500 + 2, `expected a bounded poll count, got ${polls}`);
    // A sleep separates the polls: the loop waits instead of hammering the backend.
    assert.ok(clock.state.sleeps >= polls - 1, "expected a sleep between polls");
  });

  it("counts a throwing poll as finished", async () => {
    const clock = fakeClock();
    const result = await waitForRunsToFinish(["a", "b"], {
      isRunning: async (id) => {
        if (id === "a") throw new Error("flaky network");
        return false;
      },
      sleep: clock.sleep,
      now: clock.now,
    });
    assert.equal(result, "finished");
    assert.equal(clock.state.sleeps, 0);
  });

  it("never polls a falsy id, and finishes at once with no ids", async () => {
    const clock = fakeClock();
    const polled: string[] = [];
    const result = await waitForRunsToFinish(["a", undefined, null, ""], {
      isRunning: async (id) => {
        polled.push(id);
        return false;
      },
      sleep: clock.sleep,
      now: clock.now,
    });
    assert.equal(result, "finished");
    assert.deepEqual(polled, ["a"]);

    let slept = false;
    let polledEmpty = false;
    const empty = await waitForRunsToFinish([], {
      isRunning: async () => {
        polledEmpty = true;
        return true;
      },
      sleep: async () => {
        slept = true;
      },
      now: clock.now,
    });
    assert.equal(empty, "finished");
    assert.equal(polledEmpty, false);
    assert.equal(slept, false);
  });

  it("lets a beforePoll exception propagate and stops polling", async () => {
    const clock = fakeClock();
    let polls = 0;
    let calls = 0;
    await assert.rejects(
      waitForRunsToFinish(["a"], {
        isRunning: async () => {
          polls++;
          return true;
        },
        beforePoll: () => {
          if (++calls > 2) throw new Error("cancelled");
        },
        sleep: clock.sleep,
        now: clock.now,
      }),
      /cancelled/,
    );
    assert.equal(polls, 2);
  });
});

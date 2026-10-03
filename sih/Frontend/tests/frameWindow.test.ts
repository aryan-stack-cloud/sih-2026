import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  FRAME_WINDOW,
  DECISION_WINDOW,
  appendSpectrumFrame,
  applyFalseAlarms,
  appendDecision,
  decisionForStep,
} from "../src/lib/frameWindow.ts";
import type { WsFrame } from "../src/types/contract.ts";
import type { SpectrumFrame } from "../src/lib/frameWindow.ts";

function spectrumFrame(t: number): WsFrame {
  return {
    type: "spectrum_update",
    t,
    active_bands: [t % 4],
    scanned_bands: [0],
    detected_bands: [],
  };
}

function storedFrame(t: number): SpectrumFrame {
  return {
    t,
    activeBands: [],
    scannedBands: [],
    detectedBands: [],
    falseAlarmBands: [],
  };
}

function decision(t: number): WsFrame {
  return { type: "scan_decision", t, action: t };
}

describe("appendSpectrumFrame", () => {
  it("caps the window at 40 and keeps the newest", () => {
    let frames: SpectrumFrame[] = [];
    for (let t = 0; t < FRAME_WINDOW + 10; t++) {
      frames = appendSpectrumFrame(frames, spectrumFrame(t));
    }
    assert.equal(frames.length, FRAME_WINDOW);
    assert.equal(frames[0].t, 10);
    assert.equal(frames[frames.length - 1].t, FRAME_WINDOW + 9);
  });

  it("keeps frames in arrival order", () => {
    let frames: SpectrumFrame[] = [];
    for (const t of [7, 3, 9]) {
      frames = appendSpectrumFrame(frames, spectrumFrame(t));
    }
    assert.deepEqual(frames.map((f) => f.t), [7, 3, 9]);
  });

  it("builds the stored frame from the spectrum_update fields", () => {
    const frames = appendSpectrumFrame([], {
      type: "spectrum_update",
      t: 5,
      active_bands: [1, 2],
      scanned_bands: [0, 1],
      detected_bands: [1],
    });
    assert.deepEqual(frames, [
      {
        t: 5,
        activeBands: [1, 2],
        scannedBands: [0, 1],
        detectedBands: [1],
        falseAlarmBands: [],
      },
    ]);
  });
});

describe("applyFalseAlarms", () => {
  it("attaches false alarms to the frame with the matching t only", () => {
    const frames = [storedFrame(1), storedFrame(2), storedFrame(3)];
    const next = applyFalseAlarms(frames, {
      type: "detection_event",
      t: 2,
      false_alarm_bands: [4],
    });
    assert.deepEqual(next.map((f) => f.falseAlarmBands), [[], [4], []]);
  });

  it("returns the same array reference when no t matches", () => {
    const frames = [storedFrame(1), storedFrame(2)];
    const next = applyFalseAlarms(frames, {
      type: "detection_event",
      t: 9,
      false_alarm_bands: [4],
    });
    assert.equal(next, frames);
  });

  it("returns the same array reference when there are no false alarms", () => {
    const frames = [storedFrame(1)];
    assert.equal(applyFalseAlarms(frames, { type: "detection_event", t: 1 }), frames);
    assert.equal(
      applyFalseAlarms(frames, { type: "detection_event", t: 1, false_alarm_bands: [] }),
      frames,
    );
  });
});

describe("appendDecision / decisionForStep", () => {
  it("caps decisions at 64 keeping the newest", () => {
    let decisions: WsFrame[] = [];
    for (let t = 0; t < DECISION_WINDOW + 5; t++) {
      decisions = appendDecision(decisions, decision(t));
    }
    assert.equal(decisions.length, DECISION_WINDOW);
    assert.equal(decisions[0].t, 5);
    assert.equal(decisions[decisions.length - 1].t, DECISION_WINDOW + 4);
  });

  it("returns the exact match for the requested step", () => {
    const decisions = [decision(1), decision(3), decision(5)];
    assert.equal(decisionForStep(decisions, 3)?.t, 3);
  });

  it("falls back to the latest decision at or below the step", () => {
    const decisions = [decision(1), decision(3), decision(5)];
    assert.equal(decisionForStep(decisions, 4)?.t, 3);
    assert.equal(decisionForStep(decisions, 99)?.t, 5);
  });

  it("returns null when empty or when every decision is newer than the step", () => {
    assert.equal(decisionForStep([], 4), null);
    assert.equal(decisionForStep([decision(6), decision(8)], 4), null);
  });
});

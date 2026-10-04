/**
 * Pure windowing helpers for the live spectrum stream (no runtime imports).
 *
 * <p>The store and the run watcher both fold WebSocket frames into rolling windows; the logic
 * lives here so the two stay identical and so it can be unit-tested without React. This module
 * must stay import-free at runtime: the `node --test` suite imports it with an explicit `.ts`
 * extension under type stripping, so only `import type` and erasable TypeScript are allowed.
 */

import type { WsFrame } from "../types/contract";

/** Rolling window of recent frames; the harness shows the tail, not the whole run. */
export const FRAME_WINDOW = 40;

export interface SpectrumFrame {
  t: number;
  activeBands: number[];
  scannedBands: number[];
  detectedBands: number[];
  /** Filled in by the detection_event frame, which is never coalesced away. */
  falseAlarmBands: number[];
}

/** Builds the stored frame for a `spectrum_update` and keeps the last `FRAME_WINDOW`. */
export function appendSpectrumFrame(frames: SpectrumFrame[], frame: WsFrame): SpectrumFrame[] {
  return [
    ...frames,
    {
      t: frame.t ?? 0,
      activeBands: frame.active_bands ?? [],
      scannedBands: frame.scanned_bands ?? [],
      detectedBands: frame.detected_bands ?? [],
      falseAlarmBands: [],
    },
  ].slice(-FRAME_WINDOW);
}

/**
 * Attaches a `detection_event`'s false alarms to the frame with the same `t`.
 *
 * Returns the same array reference when nothing changes (no false alarms, or no frame with
 * that `t`), so callers can skip downstream work on a referential-equality check.
 */
export function applyFalseAlarms(frames: SpectrumFrame[], frame: WsFrame): SpectrumFrame[] {
  if (!frame.false_alarm_bands?.length) return frames;
  if (!frames.some((f) => f.t === frame.t)) return frames;
  const falseAlarmBands = frame.false_alarm_bands ?? [];
  return frames.map((f) => (f.t === frame.t ? { ...f, falseAlarmBands } : f));
}

/** Rolling window of recent scheduler decisions; longer than the spectrum tail. */
export const DECISION_WINDOW = 64;

/** Appends a `scan_decision` frame and keeps the last `DECISION_WINDOW`. */
export function appendDecision(decisions: WsFrame[], frame: WsFrame): WsFrame[] {
  return [...decisions, frame].slice(-DECISION_WINDOW);
}

/**
 * The decision for a step: the one stamped with exactly `t`, else the latest one stamped at
 * or below it (the server coalesces, so `t` jumps and an exact hit is not guaranteed), else
 * `null` when no decision is old enough yet.
 */
export function decisionForStep(decisions: WsFrame[], t: number): WsFrame | null {
  let exact: WsFrame | null = null;
  let fallback: WsFrame | null = null;
  let fallbackT = -Infinity;
  for (const decision of decisions) {
    if (decision.t === undefined) continue;
    if (decision.t === t) {
      exact = decision;
    } else if (decision.t < t && decision.t >= fallbackT) {
      fallback = decision;
      fallbackT = decision.t;
    }
  }
  return exact ?? fallback;
}

/**
 * Live readouts derived from the running per-band counters (no runtime imports).
 *
 * <p>The live snapshot carries no `metrics` object until the run ends, so the race columns
 * and the "This run" tiles would show nothing for most of the run. The per-band counters
 * are cumulative over the whole run so far, which makes them converge to the final metrics:
 * spectrum heard is `sum(heard) / sum(active)` and listening efficiency is
 * `sum(useful) / sum(looks)`. Once the final `metrics` land they win, being authoritative.
 *
 * <p>This module must stay import-free at runtime: the `node --test` suite imports it with
 * an explicit `.ts` extension under type stripping, so only `import type` and erasable
 * TypeScript are allowed.
 */

import type { PerBandCounters } from "../types/contract";

export interface LiveReadouts {
  pd: number | null;
  scanEfficiency: number | null;
}

const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

/** Sums the entries, or null when the array is missing or any entry is not finite. */
function finiteSum(values: number[] | undefined): number | null {
  if (!values) return null;
  let total = 0;
  for (const v of values) {
    if (!finite(v)) return null;
    total += v;
  }
  return total;
}

/** A ratio that is null when either side is missing or the denominator is zero. */
function ratio(numerator: number[] | undefined, denominator: number[] | undefined): number | null {
  const top = finiteSum(numerator);
  const bottom = finiteSum(denominator);
  if (top === null || bottom === null || bottom === 0) return null;
  return top / bottom;
}

/**
 * Resolves each readout independently: a finite final `metrics` value wins, otherwise the
 * value is derived from the cumulative `per_band` counters (null when underivable - an
 * older Backend omits `useful`, so efficiency stays null while pd still resolves).
 */
export function liveReadouts(
  live: { metrics?: { pd: number; scan_efficiency: number }; per_band?: PerBandCounters } | null | undefined,
): LiveReadouts {
  const metricPd = live?.metrics?.pd;
  const metricEfficiency = live?.metrics?.scan_efficiency;
  return {
    pd: finite(metricPd) ? metricPd : ratio(live?.per_band?.heard, live?.per_band?.active),
    scanEfficiency: finite(metricEfficiency)
      ? metricEfficiency
      : ratio(live?.per_band?.useful, live?.per_band?.looks),
  };
}

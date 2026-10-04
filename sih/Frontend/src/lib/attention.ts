/**
 * Attention-vs-activity shares for the judge view (no runtime imports).
 *
 * <p>The per-band counters arrive inside the live snapshot, so the overlap between where the
 * transmissions happened and where the receiver looked is derivable client-side - no backend
 * change needed. This module must stay import-free at runtime: the `node --test` suite imports
 * it with an explicit `.ts` extension under type stripping, so only `import type` and erasable
 * TypeScript are allowed.
 */

import type { PerBandCounters } from "../types/contract";

export interface AttentionShares {
  looks: number[];
  active: number[];
  total: { looks: number; active: number };
}

/**
 * Normalises the look and activity counters to shares summing to 1. A side with no counts
 * yields all zeros rather than NaNs, so an idle run renders an empty state instead of garbage.
 */
export function attentionShares(perBand: PerBandCounters): AttentionShares {
  const n = Math.max(perBand.looks.length, perBand.active.length);
  let looksTotal = 0;
  let activeTotal = 0;
  for (let b = 0; b < n; b++) {
    looksTotal += perBand.looks[b] ?? 0;
    activeTotal += perBand.active[b] ?? 0;
  }
  const looks: number[] = [];
  const active: number[] = [];
  for (let b = 0; b < n; b++) {
    looks.push(looksTotal === 0 ? 0 : (perBand.looks[b] ?? 0) / looksTotal);
    active.push(activeTotal === 0 ? 0 : (perBand.active[b] ?? 0) / activeTotal);
  }
  return { looks, active, total: { looks: looksTotal, active: activeTotal } };
}

/**
 * Overlap of the two shapes: the share of listening time that went where the signals were.
 * 1 means listening exactly where the signals are, 0 means nowhere near; 0 also when either
 * side has nothing to compare. `heard` plays no part - it counts outcomes, not attention.
 */
export function matchScore(perBand: PerBandCounters): number {
  const shares = attentionShares(perBand);
  if (shares.total.looks === 0 || shares.total.active === 0) return 0;
  let score = 0;
  for (let b = 0; b < shares.looks.length; b++) {
    score += Math.min(shares.looks[b] ?? 0, shares.active[b] ?? 0);
  }
  return score;
}

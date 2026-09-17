package com.rfscheduler.metrics;

import java.util.List;

/**
 * Everything Equation 10.1 needs that is not in the DetectionOutcome itself.
 *
 * @param timeSinceLastScan  per band, measured BEFORE this step's state update
 * @param highPriorityActive per band, ground truth active and priority &gt; 1
 * @param scannedBands       bands actually observed this step
 * @param latencyHorizon     L(t) normaliser: latency at or beyond this scores 1.0
 * @param redundantWindow    a re-scan within this many steps that yields nothing new
 */
public record RewardContext(
        int[] timeSinceLastScan,
        boolean[] highPriorityActive,
        List<Integer> scannedBands,
        int latencyHorizon,
        int redundantWindow) {
}

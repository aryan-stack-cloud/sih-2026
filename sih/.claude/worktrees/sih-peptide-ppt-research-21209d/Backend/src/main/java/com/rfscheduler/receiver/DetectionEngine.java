package com.rfscheduler.receiver;

import com.rfscheduler.simulation.GroundTruth;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Applies the detection threshold to an Observation, emitting TP/FN/FP/TN events.
 *
 * <p>Classification follows PRD Section 9.1 exactly:
 *
 * <ul>
 *   <li>TP - observation exceeds threshold and ground truth is active
 *   <li>FN - ground truth active but the band was not scanned, OR scanned and below threshold
 *   <li>FP - observation exceeds threshold but ground truth is inactive
 *   <li>TN - scanned, inactive, and below threshold
 * </ul>
 *
 * <p>Note the asymmetry, and it is deliberate. FN includes bands nobody scanned - that is the
 * whole cost of a bad schedule - but FP and TN only exist for bands that were actually observed,
 * because an unscanned band cannot raise a false alarm. MetricsEngine relies on this when it
 * computes Pd across all bands but Pfa across scanned bands only.
 */
public class DetectionEngine {

    private final double threshold;

    /** (band, activationStart) pairs already intercepted, so L(t) is charged once per run. */
    private final Set<Long> interceptedRuns = new HashSet<>();

    public DetectionEngine(double threshold) {
        this.threshold = threshold;
    }

    public void reset() {
        interceptedRuns.clear();
    }

    public DetectionOutcome evaluate(Observation observation, GroundTruth truth) {
        int t = observation.t();
        Map<Integer, String> outcomes = new LinkedHashMap<>();
        List<Integer> detected = new ArrayList<>();
        List<Integer> falseAlarms = new ArrayList<>();
        Set<Long> detectedEmitters = new HashSet<>();
        Map<Integer, Integer> latency = new HashMap<>();
        Map<Integer, Integer> newRunLatencies = new HashMap<>();
        double maxPriority = 0.0;

        Set<Integer> scanned = observation.valid()
                ? new HashSet<>(observation.tunedBands())
                : Set.of();

        List<Integer> ordered = new ArrayList<>(scanned);
        java.util.Collections.sort(ordered);

        for (int band : ordered) {
            boolean active = truth.isActive(t, band);
            boolean above = observation.values().getOrDefault(band, Double.NEGATIVE_INFINITY)
                    > threshold;

            if (active && above) {
                outcomes.put(band, DetectionOutcome.TP);
                detected.add(band);
                long emitterId = truth.emitterIdAt(t, band);
                if (emitterId >= 0) {
                    detectedEmitters.add(emitterId);
                }
                maxPriority = Math.max(maxPriority, truth.priorityAt(t, band));

                int runStart = truth.activationStart(t, band);
                if (runStart >= 0) {
                    latency.put(band, t - runStart);
                    long key = ((long) band << 32) | (runStart & 0xFFFFFFFFL);
                    if (interceptedRuns.add(key)) {
                        newRunLatencies.put(band, t - runStart);
                    }
                }
            } else if (active) {
                outcomes.put(band, DetectionOutcome.FN);
            } else if (above) {
                outcomes.put(band, DetectionOutcome.FP);
                falseAlarms.add(band);
            } else {
                outcomes.put(band, DetectionOutcome.TN);
            }
        }

        List<Integer> unscannedMisses = new ArrayList<>();
        for (int band = 0; band < truth.numBands(); band++) {
            if (truth.isActive(t, band) && !scanned.contains(band)) {
                unscannedMisses.add(band);
            }
        }

        return new DetectionOutcome(t, outcomes, unscannedMisses, detected, falseAlarms,
                detectedEmitters, maxPriority, latency, newRunLatencies);
    }
}

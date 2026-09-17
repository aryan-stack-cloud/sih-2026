package com.rfscheduler.metrics;

import com.rfscheduler.receiver.DetectionOutcome;
import com.rfscheduler.simulation.GroundTruth;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Metrics engine - every formula in PRD Section 12.
 *
 * <pre>
 *   Pd        = TP / (TP + FN)                     primary
 *   Pfa       = FP / (FP + TN)                     primary
 *   AIT       = mean(t_detect - t_active_start)    primary
 *   HPDR      = TP_hi / (TP + FN)_hi               primary
 *   IR        = unique emitters detected / present
 *   SE        = useful scans / total scans
 *   R_total   = sum r(t)
 *   Precision, Recall, F1, Coverage, MissRate      secondary
 * </pre>
 *
 * <p>TWO COUNTING RULES, both deliberate and both load-bearing for an honest comparison:
 *
 * <ol>
 *   <li><b>Pd counts every band at every step.</b> A band that was active and never looked at is a
 *       false negative. If FN only counted scanned bands, a scanner that stared at one band
 *       forever would report a perfect Pd - which is exactly the failure mode this project exists
 *       to fix.
 *   <li><b>Pfa counts scanned bands only.</b> An unscanned band cannot raise a false alarm, so it
 *       contributes to neither FP nor TN. Counting idle unscanned bands as true negatives would
 *       drive Pfa toward zero for every policy and make the metric useless.
 * </ol>
 *
 * <p>AIT AND WHY THERE IS A CENSORED VARIANT. Section 12 defines AIT as an average over
 * detections, so it only counts activation runs a policy actually caught. That makes raw AIT a
 * trap when comparing two policies: one that intercepts <em>more</em> runs usually reports a
 * <em>worse</em> AIT, because the extra runs it caught are the hard, late ones the weaker policy
 * missed entirely. Read alone it ranks the better policy lower. {@code aitCensored} charges every
 * undetected run the full episode length, so the average is defined over all runs. Use {@code
 * ait} to describe reaction speed; use {@code aitCensored} to compare policies.
 */
public class MetricsEngine {

    private final GroundTruth truth;
    private final int numBands;

    private int tp;
    private int fn;
    private int fp;
    private int tn;
    private int tpHighPriority;
    private int fnHighPriority;
    private int steps;
    private int totalScans;
    private int usefulScans;
    private int invalidSteps;
    private int retunes;
    private double cumulativeReward;

    private final Set<Integer> bandsScanned = new HashSet<>();
    private final Set<Long> detectedEmitters = new HashSet<>();
    /** (band, activationStart) -> latency of the first interception of that run. */
    private final Map<Long, Integer> detectedRuns = new HashMap<>();

    public MetricsEngine(GroundTruth truth) {
        this.truth = truth;
        this.numBands = truth.numBands();
    }

    /** Folds one step of outcomes into the running totals. */
    public void record(DetectionOutcome outcome, boolean validObservation, boolean retuned,
                       double reward) {
        int t = outcome.t();
        steps++;
        cumulativeReward += reward;
        if (!validObservation) {
            invalidSteps++;
        }
        if (retuned) {
            retunes++;
        }

        for (Map.Entry<Integer, String> entry : outcome.outcomes().entrySet()) {
            int band = entry.getKey();
            totalScans++;
            bandsScanned.add(band);
            switch (entry.getValue()) {
                case DetectionOutcome.TP -> {
                    tp++;
                    usefulScans++;
                    if (truth.isHighPriorityActive(t, band)) {
                        tpHighPriority++;
                    }
                    int runStart = truth.activationStart(t, band);
                    if (runStart >= 0) {
                        long key = ((long) band << 32) | (runStart & 0xFFFFFFFFL);
                        detectedRuns.putIfAbsent(key, t - runStart);
                    }
                }
                case DetectionOutcome.FN -> {
                    fn++;
                    // The band was active: the scan was well aimed, just noisy.
                    usefulScans++;
                    if (truth.isHighPriorityActive(t, band)) {
                        fnHighPriority++;
                    }
                }
                case DetectionOutcome.FP -> fp++;
                case DetectionOutcome.TN -> tn++;
                default -> throw new IllegalStateException("unknown outcome " + entry.getValue());
            }
        }

        for (int band : outcome.unscannedMisses()) {
            fn++;
            if (truth.isHighPriorityActive(t, band)) {
                fnHighPriority++;
            }
        }

        detectedEmitters.addAll(outcome.detectedEmitters());
    }

    public MetricsSummary summary() {
        List<Integer> latencies = new ArrayList<>(detectedRuns.values());
        Collections.sort(latencies);

        int totalRuns = truth.totalActivationRuns();
        Set<Long> present = truth.emittersPresent();
        Set<Long> intercepted = new HashSet<>(detectedEmitters);
        intercepted.retainAll(present);

        double pd = safeDiv(tp, tp + fn);
        double precision = safeDiv(tp, tp + fp);
        double ait = latencies.isEmpty() ? 0.0
                : latencies.stream().mapToInt(Integer::intValue).average().orElse(0.0);

        long latencySum = latencies.stream().mapToLong(Integer::longValue).sum();
        int undetected = Math.max(0, totalRuns - latencies.size());
        double aitCensored = totalRuns == 0 ? 0.0
                : (latencySum + (long) undetected * steps) / (double) totalRuns;

        return new MetricsSummary(
                pd,
                safeDiv(fp, fp + tn),
                ait,
                aitCensored,
                safeDiv(tpHighPriority, tpHighPriority + fnHighPriority),
                latencies.isEmpty() ? 0.0 : median(latencies),
                safeDiv(intercepted.size(), present.size()),
                safeDiv(usefulScans, totalScans),
                cumulativeReward,
                precision,
                pd,
                safeDiv(2 * precision * pd, precision + pd),
                safeDiv(bandsScanned.size(), numBands),
                1.0 - pd,
                tp, fn, fp, tn,
                tpHighPriority, fnHighPriority,
                steps, totalScans, usefulScans, invalidSteps, retunes,
                detectedRuns.size(), totalRuns,
                safeDiv(detectedRuns.size(), totalRuns));
    }

    private static double median(List<Integer> sorted) {
        int n = sorted.size();
        return n % 2 == 1
                ? sorted.get(n / 2)
                : (sorted.get(n / 2 - 1) + sorted.get(n / 2)) / 2.0;
    }

    private static double safeDiv(double num, double den) {
        return den == 0 ? 0.0 : num / den;
    }
}

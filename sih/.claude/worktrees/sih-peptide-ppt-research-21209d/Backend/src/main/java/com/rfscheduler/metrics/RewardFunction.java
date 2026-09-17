package com.rfscheduler.metrics;

import com.rfscheduler.receiver.DetectionOutcome;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Set;

/**
 * Reward function - PRD Equation 10.1 / ML-003.
 *
 * <pre>
 *   r(t) = w1*D(t) + w2*P(t)*D(t) - w3*L(t) - w4*F(t) - w5*C(t) - w6*M(t)
 * </pre>
 *
 * <p>THIS IS THE AUTHORITATIVE IMPLEMENTATION. The Backend computes the reward and posts the
 * scalar to Ai-ml-1's {@code /internal/learn}; Ai-ml-1 consumes it and does not recompute it.
 * Ai-ml-1 carries its own copy in {@code ml/environments/reward.py} purely so standalone training
 * runs have a reward when no Backend is in the loop.
 *
 * <p>The two must agree, or the policy is trained against one objective and scored against
 * another - which fails silently, with no error anywhere, just worse numbers. That is what
 * {@code RewardFunctionParityTest} exists to prevent: it ports Ai-ml-1's hand-computed cases
 * verbatim and asserts this implementation reproduces them.
 *
 * <p>Two readings of Equation 10.1 are non-obvious and were settled by measurement on the ML
 * side. Both are reproduced here deliberately:
 *
 * <ul>
 *   <li><b>L(t) is charged only on the first interception of an activation run.</b> A long-lived
 *       emitter we are already tracking is not "late" on every subsequent step. Charging stale
 *       latency per step made the reward fight the metric it serves - AIT counts one latency per
 *       run while Pd rewards every active cell observed - and pushed the scheduler off emitters
 *       it had correctly found.
 *   <li><b>C(t) counts re-detecting an already-intercepted run as "no new information".</b> The
 *       literal wording is "cost of rescanning a band with no new information". Reading that as
 *       merely "found nothing" leaves camping on one loud emitter completely unpenalised, and the
 *       policy then maximises detection density on a handful of bands while never discovering the
 *       rest of the spectrum.
 * </ul>
 */
public class RewardFunction {

    private final RewardWeights weights;

    public RewardFunction(RewardWeights weights) {
        this.weights = weights == null ? RewardWeights.defaults() : weights;
    }

    public RewardWeights weights() {
        return weights;
    }

    /** Computes r(t) and reports each term of Equation 10.1 separately. */
    public RewardResult compute(DetectionOutcome outcome, RewardContext context) {
        // D(t): 1 if a true detection occurred on a scanned band at t.
        double d = outcome.hasDetection() ? 1.0 : 0.0;

        // P(t): priority multiplier of the detected emitter (>= 1); 0 when nothing was detected,
        // so the w2 term vanishes rather than paying a baseline priority for a miss.
        double p = d > 0 ? outcome.maxDetectedPriority() : 0.0;

        // L(t): normalised detection latency, charged once per activation run.
        double l = 0.0;
        if (!outcome.newRunLatencies().isEmpty()) {
            int worst = outcome.newRunLatencies().values().stream()
                    .mapToInt(Integer::intValue).max().orElse(0);
            l = Math.min((double) worst / Math.max(1, context.latencyHorizon()), 1.0);
        }

        // F(t): 1 if a false alarm occurred.
        double f = outcome.hasFalseAlarm() ? 1.0 : 0.0;

        double c = redundant(outcome, context);
        double m = missed(outcome, context);

        double reward = weights.w1Detection() * d
                + weights.w2Priority() * p * d
                - weights.w3Latency() * l
                - weights.w4FalseAlarm() * f
                - weights.w5Redundant() * c
                - weights.w6Missed() * m;

        Map<String, Double> terms = new LinkedHashMap<>();
        terms.put("D", d);
        terms.put("P", p);
        terms.put("L", l);
        terms.put("F", f);
        terms.put("C", c);
        terms.put("M", m);
        return new RewardResult(reward, terms);
    }

    /**
     * C(t): the fraction of this step's scanned bands that were revisited within the window and
     * returned nothing new. "Nothing new" includes re-detecting a run already intercepted.
     */
    private static double redundant(DetectionOutcome outcome, RewardContext context) {
        if (context.scannedBands().isEmpty()) {
            return 0.0;
        }
        Set<Integer> informative = outcome.newRunLatencies().keySet();
        int wasted = 0;
        for (int band : context.scannedBands()) {
            if (!informative.contains(band)
                    && context.timeSinceLastScan()[band] <= context.redundantWindow()) {
                wasted++;
            }
        }
        return (double) wasted / context.scannedBands().size();
    }

    /** M(t): fraction of currently-active high-priority bands left unscanned this step. */
    private static double missed(DetectionOutcome outcome, RewardContext context) {
        int totalHigh = 0;
        for (boolean high : context.highPriorityActive()) {
            if (high) {
                totalHigh++;
            }
        }
        if (totalHigh == 0) {
            return 0.0;
        }
        int missedHigh = 0;
        for (int band : outcome.unscannedMisses()) {
            if (context.highPriorityActive()[band]) {
                missedHigh++;
            }
        }
        return (double) missedHigh / totalHigh;
    }

    /** The scalar plus its per-term breakdown, so a disagreement localises to one term. */
    public record RewardResult(double reward, Map<String, Double> terms) {
    }
}

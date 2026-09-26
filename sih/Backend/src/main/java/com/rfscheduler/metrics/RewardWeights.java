package com.rfscheduler.metrics;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * w1..w6 of PRD Equation 10.1. Non-negative by definition, config-driven, logged per experiment.
 */
public record RewardWeights(
        double w1Detection,
        double w2Priority,
        double w3Latency,
        double w4FalseAlarm,
        double w5Redundant,
        double w6Missed) {

    public RewardWeights {
        Map<String, Double> all = new LinkedHashMap<>();
        all.put("w1_detection", w1Detection);
        all.put("w2_priority", w2Priority);
        all.put("w3_latency", w3Latency);
        all.put("w4_false_alarm", w4FalseAlarm);
        all.put("w5_redundant", w5Redundant);
        all.put("w6_missed", w6Missed);
        for (Map.Entry<String, Double> e : all.entrySet()) {
            if (e.getValue() < 0) {
                throw new IllegalArgumentException(
                        "reward weight " + e.getKey() + " must be non-negative");
            }
        }
    }

    /**
     * Defaults matching Ai-ml-1's ml/environments/reward.py. These two implementations must agree
     * - the agent is trained against one and scored by the other.
     *
     * <p>w5_redundant raised 3.0 -> 8.0 (README "Reward weight w5" / IMPLEMENTATION.md's swept
     * table): at 3.0 the camping penalty tops out at -3 per step against a +10 to +16 detection,
     * so camping stays net-positive even while "penalised". The swept 8.0 point trades a Pd drop
     * (0.338 -> 0.259) for interception ratio 0.725 -> 0.900 and a *better* censored AIT
     * (812 -> 703) - the point on the frontier that matches the PS's stated primary objective
     * (intercept time, interception rate) rather than raw detection density.
     */
    public static RewardWeights defaults() {
        return new RewardWeights(10.0, 2.0, 3.0, 5.0, 8.0, 4.0);
    }

    public Map<String, Double> asMap() {
        Map<String, Double> out = new LinkedHashMap<>();
        out.put("w1_detection", w1Detection);
        out.put("w2_priority", w2Priority);
        out.put("w3_latency", w3Latency);
        out.put("w4_false_alarm", w4FalseAlarm);
        out.put("w5_redundant", w5Redundant);
        out.put("w6_missed", w6Missed);
        return out;
    }
}

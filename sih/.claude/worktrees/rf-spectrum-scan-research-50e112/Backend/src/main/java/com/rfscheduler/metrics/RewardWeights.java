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
     */
    public static RewardWeights defaults() {
        return new RewardWeights(10.0, 2.0, 3.0, 5.0, 3.0, 4.0);
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

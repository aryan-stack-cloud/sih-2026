package com.rfscheduler.simulation;

import com.rfscheduler.receiver.ReceiverConfig;
import java.util.Map;

/**
 * One of the seven experiment scenarios of PRD Section 13.
 *
 * @param episodes at least 20 per policy, for statistical stability (Section 13)
 */
public record Scenario(
        String id,
        String name,
        int bands,
        int emitters,
        int durationSteps,
        int episodes,
        long seed,
        Map<String, Double> emitterMix,
        double highPriorityFraction,
        ReceiverConfig receiver,
        Map<String, Map<String, Object>> emitterParams,
        String expectedOutcome) {
}

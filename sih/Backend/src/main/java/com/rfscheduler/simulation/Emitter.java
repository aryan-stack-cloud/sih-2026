package com.rfscheduler.simulation;

import java.util.Map;

/**
 * One synthetic emitter and the parameters of its behavior class (PRD Section 8.1).
 *
 * <p>{@code priority} is the threat/priority multiplier P(t) of reward Equation 10.1 and the
 * high-priority flag behind HPDR (Section 12). It is &gt;= 1 by definition.
 */
public record Emitter(
        long emitterId,
        String behaviorClass,
        int[] bands,
        double priority,
        Map<String, Object> params) {

    public Emitter {
        if (!EmitterBehavior.CLASSES.contains(behaviorClass)) {
            throw new IllegalArgumentException(
                    "unknown behavior_class '" + behaviorClass + "'; must be one of "
                            + EmitterBehavior.CLASSES + " (API_CONTRACT.md Section 6)");
        }
        if (priority < 1.0) {
            throw new IllegalArgumentException("priority is a multiplier >= 1 (PRD Equation 10.1)");
        }
        if (bands == null || bands.length == 0) {
            throw new IllegalArgumentException("emitter must be assigned at least one band");
        }
        params = params == null ? Map.of() : Map.copyOf(params);
    }

    public int primaryBand() {
        return bands[0];
    }

    public boolean isHighPriority() {
        return priority > 1.0;
    }

    public int intParam(String key, int fallback) {
        Object v = params.get(key);
        return v instanceof Number n ? n.intValue() : fallback;
    }

    public double doubleParam(String key, double fallback) {
        Object v = params.get(key);
        return v instanceof Number n ? n.doubleValue() : fallback;
    }
}

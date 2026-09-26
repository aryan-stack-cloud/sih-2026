package com.rfscheduler.simulation;

import java.util.ArrayList;
import java.util.List;
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
        Map<String, Object> params,
        SwitchingPlan switching) {

    public Emitter(long emitterId, String behaviorClass, int[] bands,
                   double priority, Map<String, Object> params) {
        this(emitterId, behaviorClass, bands, priority, params, null);
    }

    public record Regime(int start, int end, String behaviorClass, int[] bands,
                         Map<String, Object> params) {
    }

    public static final class SwitchingPlan {
        private final int meanSteps;
        private final int minSteps;
        private final int numBands;
        private final Map<String, Double> mix;
        private final Map<String, Map<String, Object>> paramsByClass;
        private final List<Regime> regimes = new ArrayList<>();

        public SwitchingPlan(int meanSteps, int minSteps, int numBands,
                             Map<String, Double> mix,
                             Map<String, Map<String, Object>> paramsByClass) {
            if (minSteps < 1 || meanSteps < minSteps) {
                throw new IllegalArgumentException(
                        "switching requires 1 <= min_regime_steps <= mean_regime_steps");
            }
            this.meanSteps = meanSteps;
            this.minSteps = minSteps;
            this.numBands = numBands;
            this.mix = Map.copyOf(mix);
            this.paramsByClass = Map.copyOf(paramsByClass);
        }

        public int meanSteps() { return meanSteps; }
        public int minSteps() { return minSteps; }
        public int numBands() { return numBands; }
        public Map<String, Double> mix() { return mix; }
        public Map<String, Map<String, Object>> paramsByClass() { return paramsByClass; }
        public List<Regime> regimes() { return List.copyOf(regimes); }
        void clearRegimes() { regimes.clear(); }
        void addRegime(Regime regime) { regimes.add(regime); }
    }

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

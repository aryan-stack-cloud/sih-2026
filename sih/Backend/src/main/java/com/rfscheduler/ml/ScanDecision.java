package com.rfscheduler.ml;

import java.util.Map;

/**
 * One scan decision - the response shape of {@code /internal/decide}.
 *
 * @param nextBand       band to tune to
 * @param dwellTime      optional dwell control (V2 only); null for the MVP action space
 * @param modelId        which model produced it, for the decision log
 * @param decisionId     correlation id to pass back on {@code /internal/learn}
 * @param fromMl         false when this came from the local fallback rather than Ai-ml-1
 * @param indexBreakdown per-component contributions of the index policy, for the judge view;
 *                       null when the policy is not the index or Ai-ml-1 did not send one
 * @param decisionSource which policy family produced the decision ("index", ...); null when unknown
 */
public record ScanDecision(
        int nextBand,
        Integer dwellTime,
        String modelId,
        String decisionId,
        boolean fromMl,
        Map<String, Double> indexBreakdown,
        String decisionSource) {

    public ScanDecision(
            int nextBand,
            Integer dwellTime,
            String modelId,
            String decisionId,
            boolean fromMl) {
        this(nextBand, dwellTime, modelId, decisionId, fromMl, null, null);
    }

    public static ScanDecision local(int nextBand, String policy) {
        return new ScanDecision(nextBand, null, "local_" + policy, null, false);
    }
}

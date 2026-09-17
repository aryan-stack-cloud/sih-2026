package com.rfscheduler.ml;

/**
 * One scan decision - the response shape of {@code /internal/decide}.
 *
 * @param nextBand   band to tune to
 * @param dwellTime  optional dwell control (V2 only); null for the MVP action space
 * @param modelId    which model produced it, for the decision log
 * @param decisionId correlation id to pass back on {@code /internal/learn}
 * @param fromMl     false when this came from the local fallback rather than Ai-ml-1
 */
public record ScanDecision(
        int nextBand,
        Integer dwellTime,
        String modelId,
        String decisionId,
        boolean fromMl) {

    public static ScanDecision local(int nextBand, String policy) {
        return new ScanDecision(nextBand, null, "local_" + policy, null, false);
    }
}

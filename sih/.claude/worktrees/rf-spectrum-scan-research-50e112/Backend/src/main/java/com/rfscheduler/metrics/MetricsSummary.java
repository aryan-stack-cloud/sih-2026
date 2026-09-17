package com.rfscheduler.metrics;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * One run's scored metrics (PRD Section 12). Field names are what the API surfaces.
 *
 * <p>{@code aitCensored} sits alongside {@code ait} on purpose - see {@link MetricsEngine} for why
 * raw AIT cannot be used to rank two policies against each other.
 */
public record MetricsSummary(
        double pd,
        double pfa,
        double ait,
        double aitCensored,
        double hpdr,
        double medianLatency,
        double interceptionRatio,
        double scanEfficiency,
        double cumulativeReward,
        double precision,
        double recall,
        double f1,
        double coverage,
        double missRate,
        int tp,
        int fn,
        int fp,
        int tn,
        int tpHighPriority,
        int fnHighPriority,
        int steps,
        int totalScans,
        int usefulScans,
        int invalidSteps,
        int retunes,
        int detectedRuns,
        int totalRuns,
        double runInterceptRate) {

    /** Flat map for JSON responses and experiment result storage. */
    public Map<String, Object> asMap() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("pd", pd);
        m.put("pfa", pfa);
        m.put("ait", ait);
        m.put("ait_censored", aitCensored);
        m.put("hpdr", hpdr);
        m.put("median_latency", medianLatency);
        m.put("interception_ratio", interceptionRatio);
        m.put("scan_efficiency", scanEfficiency);
        m.put("cumulative_reward", cumulativeReward);
        m.put("precision", precision);
        m.put("recall", recall);
        m.put("f1", f1);
        m.put("coverage", coverage);
        m.put("miss_rate", missRate);
        m.put("run_intercept_rate", runInterceptRate);
        m.put("detected_runs", detectedRuns);
        m.put("total_runs", totalRuns);
        m.put("steps", steps);
        m.put("total_scans", totalScans);
        m.put("useful_scans", usefulScans);
        m.put("invalid_steps", invalidSteps);
        m.put("retunes", retunes);
        m.put("counts", Map.of("tp", tp, "fn", fn, "fp", fp, "tn", tn));
        return m;
    }

    /**
     * Pools several episodes into one summary.
     *
     * <p>Rates are recomputed from pooled counts rather than averaged: averaging ratios across
     * episodes of differing activity silently weights a quiet episode as heavily as a busy one.
     */
    public static Map<String, Object> aggregate(List<MetricsSummary> episodes) {
        if (episodes.isEmpty()) {
            return Map.of();
        }
        int tp = 0;
        int fn = 0;
        int fp = 0;
        int tn = 0;
        int tpHi = 0;
        int fnHi = 0;
        int useful = 0;
        int scans = 0;
        int detectedRuns = 0;
        int totalRuns = 0;
        int invalid = 0;
        int retunes = 0;
        double latencySum = 0;
        double censoredSum = 0;
        double coverage = 0;
        double interception = 0;
        double rewardSum = 0;

        for (MetricsSummary e : episodes) {
            tp += e.tp();
            fn += e.fn();
            fp += e.fp();
            tn += e.tn();
            tpHi += e.tpHighPriority();
            fnHi += e.fnHighPriority();
            useful += e.usefulScans();
            scans += e.totalScans();
            detectedRuns += e.detectedRuns();
            totalRuns += e.totalRuns();
            invalid += e.invalidSteps();
            retunes += e.retunes();
            latencySum += e.ait() * e.detectedRuns();
            censoredSum += e.aitCensored() * e.totalRuns();
            coverage += e.coverage();
            interception += e.interceptionRatio();
            rewardSum += e.cumulativeReward();
        }

        double pd = div(tp, tp + fn);
        double precision = div(tp, tp + fp);
        int n = episodes.size();

        Map<String, Object> out = new LinkedHashMap<>();
        out.put("episodes", n);
        out.put("pd", pd);
        out.put("pfa", div(fp, fp + tn));
        out.put("ait", div(latencySum, detectedRuns));
        out.put("ait_censored", div(censoredSum, totalRuns));
        out.put("hpdr", div(tpHi, tpHi + fnHi));
        out.put("interception_ratio", interception / n);
        out.put("scan_efficiency", div(useful, scans));
        out.put("precision", precision);
        out.put("recall", pd);
        out.put("f1", div(2 * precision * pd, precision + pd));
        out.put("coverage", coverage / n);
        out.put("miss_rate", 1.0 - pd);
        out.put("cumulative_reward_mean", rewardSum / n);
        out.put("detected_runs", detectedRuns);
        out.put("total_runs", totalRuns);
        out.put("run_intercept_rate", div(detectedRuns, totalRuns));
        out.put("invalid_steps", invalid);
        out.put("retunes", retunes);
        out.put("counts", Map.of("tp", tp, "fn", fn, "fp", fp, "tn", tn));
        return out;
    }

    private static double div(double num, double den) {
        return den == 0 ? 0.0 : num / den;
    }
}

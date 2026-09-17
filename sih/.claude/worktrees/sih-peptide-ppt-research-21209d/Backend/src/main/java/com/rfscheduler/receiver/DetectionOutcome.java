package com.rfscheduler.receiver;

import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Per-band detection classification for one step, plus the derived reward inputs.
 *
 * @param outcomes         band -> TP/FN/FP/TN, scanned bands only
 * @param unscannedMisses  active bands nobody looked at (also false negatives)
 * @param newRunLatencies  latency of detections that intercepted a run for the FIRST time
 */
public record DetectionOutcome(
        int t,
        Map<Integer, String> outcomes,
        List<Integer> unscannedMisses,
        List<Integer> detectedBands,
        List<Integer> falseAlarmBands,
        Set<Long> detectedEmitters,
        double maxDetectedPriority,
        Map<Integer, Integer> detectionLatency,
        Map<Integer, Integer> newRunLatencies) {

    public static final String TP = "TP";
    public static final String FN = "FN";
    public static final String FP = "FP";
    public static final String TN = "TN";

    public boolean hasDetection() {
        return !detectedBands.isEmpty();
    }

    public boolean hasFalseAlarm() {
        return !falseAlarmBands.isEmpty();
    }
}

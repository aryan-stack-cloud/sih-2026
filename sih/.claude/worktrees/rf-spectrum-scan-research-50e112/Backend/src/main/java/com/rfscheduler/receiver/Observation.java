package com.rfscheduler.receiver;

import java.util.List;
import java.util.Map;

/**
 * One step of scan output (PRD Section 9.1).
 *
 * <p>{@code valid} is false when the tuning delay left too little integration time to meet the
 * dwell minimum - the receiver spent the step retuning and saw nothing.
 */
public record Observation(
        int t,
        List<Integer> tunedBands,
        Map<Integer, Double> values,
        boolean valid,
        boolean retuned,
        double snrGain) {

    public static Observation invalid(int t, List<Integer> tunedBands, boolean retuned) {
        return new Observation(t, List.copyOf(tunedBands), Map.of(), false, retuned, 0.0);
    }
}

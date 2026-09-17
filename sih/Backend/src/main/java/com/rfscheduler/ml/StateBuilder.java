package com.rfscheduler.ml;

import com.rfscheduler.receiver.Receiver;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Builds the ML-001 StateVector - API_CONTRACT.md Section 4.
 *
 * <p>This is the seam the whole architecture turns on. The Backend owns simulation state; Ai-ml-1
 * is stateless with respect to it and gets the full picture on every call. So this class must
 * produce <em>exactly</em> the JSON in Section 4: same field names, same types, same band
 * ordering. Ai-ml-1 validates it with {@code extra="forbid"}, so a stray field is a 422 rather
 * than a silent misread - but a renamed or missing one is a contract break on our side.
 *
 * <p>The two periodicity fields are NOT computed here. They are filled in from Ai-ml-2's batch
 * prediction before the vector is sent onward; see {@link SchedulerOrchestrator}. Ai-ml-1 never
 * calls Ai-ml-2 directly, which is the seam every domain is required to respect (Section 0).
 */
public class StateBuilder {

    private final int numBands;
    private final double ewmaAlpha;

    private final int[] timeSinceLastScan;
    private final double[] recentDetectionRateEwma;
    private final int[] consecutiveMisses;
    private final double[] periodicityPhase;
    private final double[] periodicityConfidence;
    private final double[] bandPriorityWeight;

    public StateBuilder(int numBands) {
        this(numBands, 0.2);
    }

    public StateBuilder(int numBands, double ewmaAlpha) {
        this.numBands = numBands;
        this.ewmaAlpha = ewmaAlpha;
        this.timeSinceLastScan = new int[numBands];
        this.recentDetectionRateEwma = new double[numBands];
        this.consecutiveMisses = new int[numBands];
        this.periodicityPhase = new double[numBands];
        this.periodicityConfidence = new double[numBands];
        this.bandPriorityWeight = new double[numBands];
        Arrays.fill(bandPriorityWeight, 1.0);
    }

    public void reset() {
        Arrays.fill(timeSinceLastScan, 0);
        Arrays.fill(recentDetectionRateEwma, 0.0);
        Arrays.fill(consecutiveMisses, 0);
        Arrays.fill(periodicityPhase, 0.0);
        Arrays.fill(periodicityConfidence, 0.0);
    }

    /** Snapshot of band ages taken BEFORE the update - C(t) asks how recently we were last here. */
    public int[] timeSinceLastScanSnapshot() {
        return Arrays.copyOf(timeSinceLastScan, numBands);
    }

    /**
     * Folds one step of scan outcomes into the per-band features.
     *
     * <p>Called after the DetectionEngine has classified the step. Unscanned bands age; scanned
     * bands have their detection-rate EWMA and consecutive-miss counter updated.
     */
    public void update(List<Integer> scannedBands, List<Integer> detectedBands) {
        for (int b = 0; b < numBands; b++) {
            timeSinceLastScan[b]++;
        }
        for (int band : scannedBands) {
            timeSinceLastScan[band] = 0;
            double hit = detectedBands.contains(band) ? 1.0 : 0.0;
            recentDetectionRateEwma[band] =
                    ewmaAlpha * hit + (1.0 - ewmaAlpha) * recentDetectionRateEwma[band];
            if (hit > 0) {
                consecutiveMisses[band] = 0;
            } else {
                consecutiveMisses[band]++;
            }
        }
    }

    /**
     * Injects Ai-ml-2's contribution before the vector goes to Ai-ml-1.
     *
     * <p>This service does not estimate periodicity and must not try to. If Ai-ml-2 is
     * unreachable these stay at zero, which Ai-ml-1 reads as "no periodicity claim" - a
     * well-formed nothing rather than a wrong guess.
     */
    public void setPeriodicity(int band, double phase, double confidence) {
        periodicityPhase[band] = clamp01(phase);
        periodicityConfidence[band] = clamp01(confidence);
    }

    public void clearPeriodicity() {
        Arrays.fill(periodicityPhase, 0.0);
        Arrays.fill(periodicityConfidence, 0.0);
    }

    public void setBandPriorityWeight(int band, double weight) {
        bandPriorityWeight[band] = weight;
    }

    /** The StateVector JSON exactly as API_CONTRACT.md Section 4 defines it. */
    public Map<String, Object> toContract(Receiver receiver) {
        List<Map<String, Object>> bands = new ArrayList<>(numBands);
        for (int b = 0; b < numBands; b++) {
            Map<String, Object> band = new LinkedHashMap<>();
            band.put("band_id", b);
            band.put("time_since_last_scan", timeSinceLastScan[b]);
            band.put("recent_detection_rate_ewma", clamp01(recentDetectionRateEwma[b]));
            band.put("consecutive_misses", consecutiveMisses[b]);
            band.put("periodicity_phase", periodicityPhase[b]);
            band.put("periodicity_confidence", periodicityConfidence[b]);
            band.put("band_priority_weight", bandPriorityWeight[b]);
            band.put("tuning_cost_to_band", receiver.tuningCostTo(b));
            bands.add(band);
        }

        Map<String, Object> receiverBlock = new LinkedHashMap<>();
        receiverBlock.put("tuned_bands", receiver.tunedBands());
        receiverBlock.put("dwell_remaining_ms", receiver.dwellRemainingMs());
        receiverBlock.put("tuning_delay_countdown_ms", receiver.tuningDelayCountdownMs());

        Map<String, Object> state = new LinkedHashMap<>();
        state.put("bands", bands);
        state.put("receiver", receiverBlock);
        return state;
    }

    public int numBands() {
        return numBands;
    }

    private static double clamp01(double v) {
        if (Double.isNaN(v)) {
            return 0.0;
        }
        return Math.max(0.0, Math.min(1.0, v));
    }
}

package com.rfscheduler.receiver;

/**
 * Configurable receiver parameters (PRD Section 9.2).
 *
 * @param bandwidthK   bands observable per step (instantaneous bandwidth)
 * @param dwellMs      minimum observation duration
 * @param tuningDelayMs cost of retuning to a different block
 * @param stepMs       wall time of one simulation step
 * @param threshold    detection threshold on the observation statistic
 * @param snrMean      mean observation value when ground truth is active
 * @param noiseSigma   standard deviation of the observation noise
 */
public record ReceiverConfig(
        int bandwidthK,
        int dwellMs,
        int tuningDelayMs,
        int stepMs,
        double threshold,
        double snrMean,
        double noiseSigma) {

    public ReceiverConfig {
        if (bandwidthK < 1) {
            throw new IllegalArgumentException("bandwidthK must be >= 1");
        }
        if (dwellMs > stepMs) {
            throw new IllegalArgumentException(
                    "dwellMs cannot exceed stepMs; the receiver could never observe");
        }
        if (tuningDelayMs < 0 || tuningDelayMs > stepMs) {
            throw new IllegalArgumentException("tuningDelayMs must be within [0, stepMs]");
        }
    }

    public static ReceiverConfig defaults() {
        return new ReceiverConfig(2, 4, 3, 10, 1.5, 3.0, 1.0);
    }

    /** Whether a step that retunes can still yield a valid observation. */
    public boolean retuneIsObservable() {
        return (stepMs - tuningDelayMs) >= dwellMs;
    }
}

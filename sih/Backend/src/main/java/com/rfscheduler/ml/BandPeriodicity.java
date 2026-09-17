package com.rfscheduler.ml;

/**
 * Ai-ml-2's contribution for one band, merged into the StateVector by the Backend.
 *
 * <p>{@code confidence} zero with a null window is a well-formed "no periodicity claim", which is
 * what Ai-ml-2 returns for the four non-periodic emitter classes and for bands it has not seen
 * enough of. It is not an error and must not be treated as one.
 */
public record BandPeriodicity(
        int bandId,
        Double estimatedPeriod,
        Double windowStart,
        Double windowEnd,
        double confidence,
        double phase) {

    public static BandPeriodicity none(int bandId) {
        return new BandPeriodicity(bandId, null, null, null, 0.0, 0.0);
    }

    public boolean hasClaim() {
        return estimatedPeriod != null && confidence > 0;
    }
}

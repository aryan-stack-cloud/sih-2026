package com.rfscheduler.receiver;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;

/** Executes a scan action against the Receiver and Spectrum, producing an Observation. */
public class Scanner {

    private final Receiver receiver;
    private final Random noise;

    public Scanner(Receiver receiver, Random noise) {
        this.receiver = receiver;
        this.noise = noise;
    }

    public Observation execute(int t, int nextBand, boolean[] occupancyRow) {
        ReceiverConfig cfg = receiver.config();
        boolean retuned = receiver.tune(nextBand);
        List<Integer> bands = receiver.tunedBands();

        int observeMs = cfg.stepMs() - (retuned ? cfg.tuningDelayMs() : 0);
        if (observeMs < cfg.dwellMs()) {
            return Observation.invalid(t, bands, retuned);
        }

        double snrGain = Math.sqrt((double) observeMs / cfg.stepMs());
        Map<Integer, Double> values = new HashMap<>();
        for (int band : bands) {
            double signal = occupancyRow[band] ? cfg.snrMean() * snrGain : 0.0;
            values.put(band, signal + noise.nextGaussian() * cfg.noiseSigma());
        }
        return new Observation(t, bands, values, true, retuned, snrGain);
    }
}

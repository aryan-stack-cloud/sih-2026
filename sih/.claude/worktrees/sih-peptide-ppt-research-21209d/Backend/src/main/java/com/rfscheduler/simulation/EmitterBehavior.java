package com.rfscheduler.simulation;

import java.util.List;
import java.util.Random;

/**
 * Emitter behavior strategies - PRD Section 8.3.
 *
 * <p>Five classes, matching {@code behavior_class} in API_CONTRACT.md Section 6: fixed, periodic,
 * agile, random, intermittent.
 *
 * <p>CROSS-LANGUAGE NOTE. Ai-ml-1 implements the same five behaviors in Python because it needs an
 * environment to train against. The two implementations share the <em>physics</em>, not the random
 * stream: Java's PRNG and NumPy's produce different sequences, so the same seed does not give a
 * byte-identical spectrum in both. That is fine and expected - a policy transfers because the
 * feature shapes and the receiver constraints match, not because the worlds are identical. What is
 * guaranteed here is that the same seed always gives the same world <em>in Java</em> (NFR-006),
 * which is what makes the baseline-vs-ML comparison a controlled experiment.
 */
public final class EmitterBehavior {

    private EmitterBehavior() {
    }

    public static final List<String> CLASSES =
            List.of("fixed", "periodic", "agile", "random", "intermittent");

    /**
     * Generates the band this emitter occupies at each step, or -1 when silent.
     *
     * @return array of length {@code duration}
     */
    public static int[] activityTrack(Emitter emitter, int duration, Random rng) {
        int[] track = new int[duration];
        java.util.Arrays.fill(track, -1);

        switch (emitter.behaviorClass()) {
            case "fixed" -> fixed(emitter, duration, rng, track);
            case "periodic" -> periodic(emitter, duration, rng, track);
            case "agile" -> agile(emitter, duration, rng, track);
            case "random" -> random(emitter, duration, rng, track);
            case "intermittent" -> intermittent(emitter, duration, rng, track);
            default -> throw new IllegalArgumentException(
                    "unknown behavior_class '" + emitter.behaviorClass()
                            + "'; must be one of " + CLASSES);
        }
        return track;
    }

    /** Continuously or near-continuously active on one assigned band. */
    private static void fixed(Emitter e, int duration, Random rng, int[] track) {
        double duty = e.doubleParam("duty", 0.95);
        for (int t = 0; t < duration; t++) {
            if (rng.nextDouble() < duty) {
                track[t] = e.primaryBand();
            }
        }
    }

    /** Active for a dwell window every Tperiod steps, constant or jittered. */
    private static void periodic(Emitter e, int duration, Random rng, int[] track) {
        int period = Math.max(1, e.intParam("period", 20));
        int onDuration = Math.max(1, e.intParam("on_duration", Math.max(1, period / 5)));
        int phase = Math.floorMod(e.intParam("phase", 0), period);
        int jitter = e.intParam("jitter", 0);

        if (jitter > 0) {
            // Jittered period: walk activation starts forward one period at a time so the jitter
            // accumulates the way a drifting clock does, rather than cancelling out.
            int start = phase;
            while (start < duration) {
                int end = Math.min(duration, start + onDuration);
                for (int t = start; t < end; t++) {
                    track[t] = e.primaryBand();
                }
                start += period + (rng.nextInt(2 * jitter + 1) - jitter);
                start = Math.max(start, end);   // never overlap the window just written
            }
        } else {
            for (int t = phase; t < duration; t++) {
                if (Math.floorMod(t - phase, period) < onDuration) {
                    track[t] = e.primaryBand();
                }
            }
        }
    }

    /** Hops across a defined band set at a given hop rate. */
    private static void agile(Emitter e, int duration, Random rng, int[] track) {
        int hopRate = Math.max(1, e.intParam("hop_rate", 5));
        double duty = e.doubleParam("duty", 0.9);
        int offset = e.intParam("hop_offset", 0);
        int[] bands = e.bands();

        for (int t = 0; t < duration; t++) {
            if (rng.nextDouble() < duty) {
                track[t] = bands[Math.floorMod(t / hopRate + offset, bands.length)];
            }
        }
    }

    /** Activates with a stochastic per-slot probability, independent across slots. */
    private static void random(Emitter e, int duration, Random rng, int[] track) {
        double p = e.doubleParam("p_active", 0.15);
        for (int t = 0; t < duration; t++) {
            if (rng.nextDouble() < p) {
                track[t] = e.primaryBand();
            }
        }
    }

    /** Bursty ON/OFF: a two-state Markov chain, geometric burst lengths and gaps. */
    private static void intermittent(Emitter e, int duration, Random rng, int[] track) {
        double pOnToOff = e.doubleParam("p_on_to_off", 0.25);
        double pOffToOn = e.doubleParam("p_off_to_on", 0.05);
        boolean active = false;

        for (int t = 0; t < duration; t++) {
            double draw = rng.nextDouble();
            if (active) {
                track[t] = e.primaryBand();
                if (draw < pOnToOff) {
                    active = false;
                }
            } else if (draw < pOffToOn) {
                active = true;
                track[t] = e.primaryBand();
            }
        }
    }
}

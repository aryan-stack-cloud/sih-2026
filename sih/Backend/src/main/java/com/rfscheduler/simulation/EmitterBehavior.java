package com.rfscheduler.simulation;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Map;
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
        if (emitter.switching() != null) {
            return switchingTrack(emitter, duration, rng);
        }
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

    private static int[] switchingTrack(Emitter emitter, int duration, Random rng) {
        Emitter.SwitchingPlan plan = emitter.switching();
        int[] track = new int[duration];
        Arrays.fill(track, -1);
        plan.clearRegimes();
        int start = 0;
        String behavior = emitter.behaviorClass();
        int[] bands = emitter.bands();
        Map<String, Object> params = emitter.params();
        while (start < duration) {
            int length = plan.minSteps()
                    + rng.nextInt(2 * (plan.meanSteps() - plan.minSteps()) + 1);
            int end = Math.min(duration, start + length);
            plan.addRegime(new Emitter.Regime(start, end, behavior,
                    Arrays.copyOf(bands, bands.length), Map.copyOf(params)));
            Emitter segment = new Emitter(emitter.emitterId(), behavior, bands,
                    emitter.priority(), params);
            int[] activity = activityTrack(segment, end - start, rng);
            System.arraycopy(activity, 0, track, start, activity.length);
            start = end;
            if (start < duration) {
                behavior = nextClass(behavior, plan.mix(), rng);
                params = EmitterFactory.randomiseParams(behavior,
                        plan.paramsByClass().getOrDefault(behavior, Map.of()), rng);
                bands = switchBands(behavior, emitter.primaryBand(), plan.numBands(), params, rng);
            }
        }
        return track;
    }

    private static String nextClass(String current, Map<String, Double> mix, Random rng) {
        double total = 0;
        for (String name : CLASSES) {
            if (!name.equals(current)) {
                total += Math.max(0, mix.getOrDefault(name, 0.0));
            }
        }
        if (total <= 0) {
            throw new IllegalArgumentException(
                    "switching requires another class with positive mix weight");
        }
        double draw = rng.nextDouble() * total;
        String last = null;
        for (String name : CLASSES) {
            double weight = name.equals(current) ? 0 : Math.max(0, mix.getOrDefault(name, 0.0));
            if (weight > 0) {
                last = name;
                draw -= weight;
                if (draw < 0) {
                    return name;
                }
            }
        }
        return last;
    }

    private static int[] switchBands(String behavior, int home, int numBands,
                                     Map<String, Object> params, Random rng) {
        if (!"agile".equals(behavior)) {
            return new int[] {home};
        }
        if (params.get("bands") instanceof List<?> pinned) {
            List<Integer> result = new ArrayList<>();
            result.add(home);
            for (Object value : pinned) {
                int band = ((Number) value).intValue();
                if (band < 0 || band >= numBands) {
                    throw new IllegalArgumentException("pinned band outside spectrum: " + band);
                }
                if (!result.contains(band)) {
                    result.add(band);
                }
            }
            return result.stream().mapToInt(Integer::intValue).toArray();
        }
        int requested = params.get("hop_set_size") instanceof Number n
                ? n.intValue() : Math.min(4, numBands);
        int size = Math.max(1, Math.min(Math.max(2, requested), numBands));
        List<Integer> pool = new ArrayList<>();
        for (int b = 0; b < numBands; b++) {
            if (b != home) {
                pool.add(b);
            }
        }
        Collections.shuffle(pool, rng);
        int[] bands = new int[size];
        bands[0] = home;
        for (int i = 1; i < size; i++) {
            bands[i] = pool.get(i - 1);
        }
        return bands;
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

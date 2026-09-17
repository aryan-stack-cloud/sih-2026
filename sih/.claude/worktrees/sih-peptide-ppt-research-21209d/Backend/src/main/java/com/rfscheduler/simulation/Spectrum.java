package com.rfscheduler.simulation;

import java.util.Arrays;
import java.util.List;
import java.util.Random;

/**
 * Owns the frequency bands and produces the ground truth for a run (PRD Section 8.1).
 *
 * <p>The whole activity table is computed once, up front, from a seeded generator. Two properties
 * the rest of the system depends on follow from that:
 *
 * <ul>
 *   <li>the same seed always gives the same world (NFR-006); and
 *   <li>every policy evaluated at that seed sees an <em>identical</em> spectrum, which is what
 *       makes the Section 13 baseline-vs-ML comparison a controlled experiment rather than two
 *       unrelated runs.
 * </ul>
 */
public class Spectrum {

    private final int numBands;

    public Spectrum(int numBands) {
        if (numBands < 1) {
            throw new IllegalArgumentException("numBands must be >= 1");
        }
        this.numBands = numBands;
    }

    public int numBands() {
        return numBands;
    }

    /**
     * Collapses every emitter activity track into one occupancy/owner table.
     *
     * <p>Where several emitters occupy the same band at the same step the highest-priority one is
     * recorded as the owner: the reward's P(t) and HPDR should reflect the most significant
     * emitter present, not an arbitrary one.
     */
    public GroundTruth generate(List<Emitter> emitters, int duration, Random rng) {
        boolean[][] occupancy = new boolean[duration][numBands];
        int[][] owner = new int[duration][numBands];
        double[][] priority = new double[duration][numBands];
        for (int[] row : owner) {
            Arrays.fill(row, -1);
        }

        for (int i = 0; i < emitters.size(); i++) {
            Emitter emitter = emitters.get(i);
            int[] track = EmitterBehavior.activityTrack(emitter, duration, rng);
            for (int t = 0; t < duration; t++) {
                int band = track[t];
                if (band < 0) {
                    continue;
                }
                occupancy[t][band] = true;
                if (emitter.priority() > priority[t][band]) {
                    priority[t][band] = emitter.priority();
                    owner[t][band] = i;
                }
            }
        }
        return new GroundTruth(occupancy, owner, priority, emitters);
    }
}

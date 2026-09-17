package com.rfscheduler.simulation;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * Pre-computed activity table plus the structures the metrics engine needs (PRD Section 8.1).
 *
 * <p>Never given to the scheduler. Section 8.1 is explicit that the GroundTruthGenerator output is
 * "used only for metric scoring, never given to the scheduler" - the policy only ever sees the
 * StateVector built from its own scan outcomes.
 *
 * <p>Alongside occupancy we keep the <em>owner</em> of each active cell so the metrics engine can
 * compute per-emitter Interception Ratio and priority-weighted HPDR, and {@code activationStarts}
 * so detection latency is measured from the moment a band went active rather than from t=0.
 */
public final class GroundTruth {

    private final boolean[][] occupancy;      // [t][band]
    private final int[][] owner;              // emitter index into emitters, or -1
    private final double[][] priority;
    private final int[][] activationStarts;   // start of the run this cell belongs to, or -1
    private final List<Emitter> emitters;
    private final int duration;
    private final int numBands;

    GroundTruth(boolean[][] occupancy, int[][] owner, double[][] priority, List<Emitter> emitters) {
        this.occupancy = occupancy;
        this.owner = owner;
        this.priority = priority;
        this.emitters = List.copyOf(emitters);
        this.duration = occupancy.length;
        this.numBands = duration == 0 ? 0 : occupancy[0].length;
        this.activationStarts = computeActivationStarts();
    }

    private int[][] computeActivationStarts() {
        int[][] starts = new int[duration][numBands];
        for (int b = 0; b < numBands; b++) {
            int runStart = -1;
            for (int t = 0; t < duration; t++) {
                if (occupancy[t][b]) {
                    if (runStart < 0) {
                        runStart = t;
                    }
                    starts[t][b] = runStart;
                } else {
                    starts[t][b] = -1;
                    runStart = -1;
                }
            }
        }
        return starts;
    }

    public int duration() {
        return duration;
    }

    public int numBands() {
        return numBands;
    }

    public boolean isActive(int t, int band) {
        return occupancy[t][band];
    }

    public boolean[] occupancyAt(int t) {
        return Arrays.copyOf(occupancy[t], numBands);
    }

    public int ownerAt(int t, int band) {
        return owner[t][band];
    }

    public double priorityAt(int t, int band) {
        return priority[t][band];
    }

    public boolean isHighPriorityActive(int t, int band) {
        return priority[t][band] > 1.0;
    }

    public int activationStart(int t, int band) {
        return activationStarts[t][band];
    }

    public List<Emitter> emitters() {
        return emitters;
    }

    /** Emitter id owning a cell, or -1 when idle. */
    public long emitterIdAt(int t, int band) {
        int index = owner[t][band];
        return index < 0 ? -1L : emitters.get(index).emitterId();
    }

    /** Total contiguous activation runs across all bands - the denominator for run coverage. */
    public int totalActivationRuns() {
        int total = 0;
        for (int b = 0; b < numBands; b++) {
            Set<Integer> starts = new HashSet<>();
            for (int t = 0; t < duration; t++) {
                if (occupancy[t][b]) {
                    starts.add(activationStarts[t][b]);
                }
            }
            total += starts.size();
        }
        return total;
    }

    public Set<Long> emittersPresent() {
        Set<Long> present = new HashSet<>();
        for (int t = 0; t < duration; t++) {
            for (int b = 0; b < numBands; b++) {
                if (owner[t][b] >= 0) {
                    present.add(emitters.get(owner[t][b]).emitterId());
                }
            }
        }
        return present;
    }

    public double occupancyRate() {
        if (duration == 0 || numBands == 0) {
            return 0.0;
        }
        long active = 0;
        for (boolean[] row : occupancy) {
            for (boolean cell : row) {
                if (cell) {
                    active++;
                }
            }
        }
        return (double) active / (duration * (long) numBands);
    }

    /** Bands active at t, for the spectrum_update WebSocket frame. */
    public List<Integer> activeBands(int t) {
        List<Integer> out = new ArrayList<>();
        for (int b = 0; b < numBands; b++) {
            if (occupancy[t][b]) {
                out.add(b);
            }
        }
        return out;
    }
}

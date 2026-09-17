package com.rfscheduler.simulation;

import java.util.Random;

/**
 * Independent random streams derived from one seed.
 *
 * <p>NFR-006 requires that an identical seed and configuration give reproducible output, and
 * Section 13 additionally requires that baseline and ML runs of the same scenario see the
 * <em>identical</em> spectrum so the comparison isolates the policy. Both fall out of one rule:
 * derive a separate stream per concern, so changing the policy cannot perturb the world.
 *
 * <pre>
 *   seed + 0   ground truth (emitter placement + activity)
 *   seed + 1   detection noise
 *   seed + 2   policy exploration
 * </pre>
 */
public final class Seeding {

    public static final int GROUND_TRUTH_STREAM = 0;
    public static final int NOISE_STREAM = 1;
    public static final int POLICY_STREAM = 2;

    private Seeding() {
    }

    public static Random stream(long seed, int streamIndex) {
        // Mix the stream index in rather than adding it, so adjacent seeds do not overlap streams.
        long mixed = seed * 0x9E3779B97F4A7C15L + streamIndex * 0xBF58476D1CE4E5B9L;
        return new Random(mixed);
    }

    public static Random groundTruth(long seed) {
        return stream(seed, GROUND_TRUTH_STREAM);
    }

    public static Random noise(long seed) {
        return stream(seed, NOISE_STREAM);
    }

    public static Random policy(long seed) {
        return stream(seed, POLICY_STREAM);
    }
}

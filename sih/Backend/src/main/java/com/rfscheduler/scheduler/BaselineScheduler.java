package com.rfscheduler.scheduler;

import java.util.List;
import java.util.Random;

/**
 * Open-loop baseline scanner - the control group (FR-005, PRD Section 3.1).
 *
 * <p>This is the legacy behaviour the whole project exists to beat: a fixed pattern that treats
 * every band as equally likely to be active at every moment, and never looks at its own scan
 * history.
 *
 * <p>Three modes. {@code ROUND_ROBIN} advances by a stride each step (defaulting to the
 * receiver's instantaneous bandwidth K, so consecutive steps tile the spectrum without overlap -
 * the fairest version of the fixed sweep). {@code FIXED_ORDER} walks a configured band list.
 * {@code RANDOM} picks uniformly, and is the reference the Ai-ml-1 acceptance gate is stated
 * against.
 *
 * <p>DESIGN NOTE. A baseline must not be constructed so that it collides with the emitters in
 * some arithmetically convenient way - a sweep and a synthetic target sharing a period produce a
 * meaningless hit rate, high or low, that says nothing about scheduling. Here the sweep is fixed
 * and the emitters come from an independent random stream, so the baseline scores whatever the
 * geometry honestly gives it.
 *
 * <p>{@link #decide} ignores all feedback. That is the definition of open loop, not an oversight.
 */
public class BaselineScheduler {

    public enum Mode { ROUND_ROBIN, FIXED_ORDER, RANDOM }

    private final int numBands;
    private final Mode mode;
    private final int stride;
    private final List<Integer> bandOrder;
    private final Random rng;

    private int stepIndex;

    public BaselineScheduler(int numBands, Mode mode, int stride, List<Integer> bandOrder,
                             Random rng) {
        if (mode == Mode.FIXED_ORDER && (bandOrder == null || bandOrder.isEmpty())) {
            throw new IllegalArgumentException("FIXED_ORDER mode requires a band order");
        }
        this.numBands = numBands;
        this.mode = mode;
        this.stride = Math.max(1, stride);
        this.bandOrder = bandOrder;
        this.rng = rng == null ? new Random(0) : rng;
    }

    public static BaselineScheduler roundRobin(int numBands, int stride) {
        return new BaselineScheduler(numBands, Mode.ROUND_ROBIN, stride, null, null);
    }

    public static BaselineScheduler random(int numBands, Random rng) {
        return new BaselineScheduler(numBands, Mode.RANDOM, 1, null, rng);
    }

    public void reset() {
        stepIndex = 0;
    }

    /** Next band to scan. Deliberately takes no state - an open-loop scanner has no feedback. */
    public int decide() {
        int band = switch (mode) {
            case FIXED_ORDER -> bandOrder.get(stepIndex % bandOrder.size());
            case RANDOM -> rng.nextInt(numBands);
            case ROUND_ROBIN -> Math.floorMod(stepIndex * stride, numBands);
        };
        stepIndex++;
        return band;
    }

    public Mode mode() {
        return mode;
    }
}

package com.rfscheduler.receiver;

import java.util.ArrayList;
import java.util.List;

/**
 * Holds instantaneous bandwidth, dwell time, tuning delay and detection threshold (PRD Section 9).
 *
 * <p>Timing model, where one simulation step is {@code stepMs} of wall time:
 *
 * <pre>
 *   observeMs = stepMs - (tuningDelayMs if the receiver retuned this step else 0)
 *
 *   observeMs &lt; dwellMs  -&gt; no valid observation at all this step. Section 9.1: "tuning delay
 *                            must fully elapse before a newly tuned band yields a valid
 *                            observation", and dwell is the minimum observation duration.
 *
 *   otherwise            -&gt; observation quality scales with integration time,
 *                            snrGain = sqrt(observeMs / stepMs)
 * </pre>
 *
 * <p>The graded SNR term matters. A hard on/off switching cost would make retuning either free or
 * fatal, and the scheduler would learn a degenerate policy either way. Scaling effective SNR by
 * integration time reproduces the real trade-off: retuning is always possible, but you see less
 * well on the step you did it.
 *
 * <p>Instantaneous bandwidth: an action names a start band, and the receiver observes the
 * contiguous block of K bands from there, wrapping at the top of the spectrum. That is what "K
 * bands observable per step" means physically (Section 9.2) and it keeps the action space one
 * integer wide, matching {@code next_band} in API_CONTRACT.md Section 4.
 */
public class Receiver {

    private final ReceiverConfig config;
    private final int numBands;

    private int tunedStart;
    private int dwellRemainingMs;
    private int tuningDelayCountdownMs;

    public Receiver(ReceiverConfig config, int numBands) {
        this.config = config;
        this.numBands = numBands;
        reset(0);
    }

    public void reset(int tunedStart) {
        this.tunedStart = Math.floorMod(tunedStart, numBands);
        this.dwellRemainingMs = 0;
        this.tuningDelayCountdownMs = 0;
    }

    /** Points the receiver at a new block. Returns true if this was an actual retune. */
    public boolean tune(int nextBand) {
        int target = Math.floorMod(nextBand, numBands);
        boolean retuned = target != tunedStart;
        tunedStart = target;
        if (retuned) {
            tuningDelayCountdownMs = config.tuningDelayMs();
            dwellRemainingMs = Math.max(0,
                    config.dwellMs() - (config.stepMs() - config.tuningDelayMs()));
        } else {
            tuningDelayCountdownMs = 0;
            dwellRemainingMs = 0;
        }
        return retuned;
    }

    public List<Integer> tunedBands() {
        List<Integer> bands = new ArrayList<>(config.bandwidthK());
        for (int i = 0; i < Math.min(config.bandwidthK(), numBands); i++) {
            bands.add(Math.floorMod(tunedStart + i, numBands));
        }
        return bands;
    }

    /** Integer cost of reaching a band from the current tuning, for the StateVector. */
    public int tuningCostTo(int band) {
        return Math.floorMod(band, numBands) == tunedStart ? 0 : 1;
    }

    public int tunedStart() {
        return tunedStart;
    }

    public int dwellRemainingMs() {
        return dwellRemainingMs;
    }

    public int tuningDelayCountdownMs() {
        return tuningDelayCountdownMs;
    }

    public ReceiverConfig config() {
        return config;
    }

    public int numBands() {
        return numBands;
    }
}

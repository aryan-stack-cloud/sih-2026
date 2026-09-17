package com.rfscheduler.simulation;

/** Advances discrete simulation time in fixed-size steps; drives every other component. */
public class SimulationClock {

    private final int durationSteps;
    private int t;

    public SimulationClock(int durationSteps) {
        this.durationSteps = durationSteps;
        this.t = 0;
    }

    public int current() {
        return t;
    }

    public boolean hasNext() {
        return t < durationSteps;
    }

    public int advance() {
        return t++;
    }

    public void resetTo(int step) {
        this.t = Math.max(0, Math.min(step, durationSteps));
    }

    public int durationSteps() {
        return durationSteps;
    }
}

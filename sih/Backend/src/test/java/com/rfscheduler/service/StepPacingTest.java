package com.rfscheduler.service;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class StepPacingTest {

    @Test
    void zeroElapsedReturnsFullDelay() {
        assertThat(SimulationRunner.remainingPaceMs(100, 0)).isEqualTo(100);
    }

    @Test
    void elapsedBelowDelayReturnsDifference() {
        assertThat(SimulationRunner.remainingPaceMs(100, 30_000_000)).isEqualTo(70);
    }

    @Test
    void elapsedEqualToDelayReturnsZero() {
        assertThat(SimulationRunner.remainingPaceMs(100, 100_000_000)).isEqualTo(0);
    }

    @Test
    void elapsedAboveDelayReturnsZero() {
        assertThat(SimulationRunner.remainingPaceMs(100, 250_000_000)).isEqualTo(0);
    }

    @Test
    void nonPositiveDelayReturnsZeroWhateverElapsed() {
        assertThat(SimulationRunner.remainingPaceMs(0, 0)).isEqualTo(0);
        assertThat(SimulationRunner.remainingPaceMs(0, 50_000_000)).isEqualTo(0);
        assertThat(SimulationRunner.remainingPaceMs(-5, 10_000_000)).isEqualTo(0);
    }

    @Test
    void subMillisecondElapsedStillReturnsFullDelay() {
        assertThat(SimulationRunner.remainingPaceMs(100, 999_999)).isEqualTo(100);
    }
}

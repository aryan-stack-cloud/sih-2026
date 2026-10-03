package com.rfscheduler.service;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class StepFrameDecisionSourceTest {

    @Test
    void oldTenArgumentConstructorLeavesBothNewValuesNull() {
        var frame = new SimulationRunner.StepFrame(0, 3, List.of(3), List.of(), List.of(),
                List.of(), 1.0, Map.of("C", 1.0), "m", true);

        assertThat(frame.decisionSource()).isNull();
        assertThat(frame.indexBreakdown()).isNull();
    }

    @Test
    void fullConstructorRoundTripsBothNewValues() {
        var frame = new SimulationRunner.StepFrame(1, 4, List.of(4), List.of(), List.of(),
                List.of(), 2.0, Map.of(), "m2", false, "index", Map.of("value", 0.5));

        assertThat(frame.decisionSource()).isEqualTo("index");
        assertThat(frame.indexBreakdown()).containsEntry("value", 0.5);
    }
}

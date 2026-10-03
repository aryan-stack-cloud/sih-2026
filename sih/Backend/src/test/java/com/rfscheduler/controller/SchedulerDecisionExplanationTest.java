package com.rfscheduler.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.rfscheduler.dto.ApiResponse;
import com.rfscheduler.ml.MlPeriodicityClient;
import com.rfscheduler.ml.MlSchedulerClient;
import com.rfscheduler.service.SimulationRunner;
import com.rfscheduler.service.SimulationService;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class SchedulerDecisionExplanationTest {

    private static SchedulerController controllerWithFrame(SimulationRunner.StepFrame frame) {
        SimulationService simulations = mock(SimulationService.class);
        SimulationService.LiveSimulation live =
                mock(SimulationService.LiveSimulation.class);
        when(simulations.liveState("s1")).thenReturn(live);
        when(live.latestFrame()).thenReturn(frame);
        return new SchedulerController(simulations, mock(MlSchedulerClient.class),
                mock(MlPeriodicityClient.class));
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> decisionOf(ApiResponse<Map<String, Object>> response) {
        return (Map<String, Object>) response.data().get("decision");
    }

    @Test
    void includesBothFieldsWhenLatestFrameHasThem() {
        var frame = new SimulationRunner.StepFrame(7, 3, List.of(3), List.of(), List.of(),
                List.of(), 1.0, Map.of("C", 1.0), "m", true, "index",
                Map.of("value", 0.5));

        Map<String, Object> decision =
                decisionOf(controllerWithFrame(frame).latestDecision("s1"));

        assertThat(decision.get("decision_source")).isEqualTo("index");
        assertThat(decision.get("index_breakdown")).isEqualTo(Map.of("value", 0.5));
    }

    @Test
    void omitsBothFieldsWhenLatestFrameLacksThem() {
        var frame = new SimulationRunner.StepFrame(7, 3, List.of(3), List.of(), List.of(),
                List.of(), 1.0, Map.of("C", 1.0), "m", true);

        Map<String, Object> decision =
                decisionOf(controllerWithFrame(frame).latestDecision("s1"));

        assertThat(decision).doesNotContainKeys("decision_source", "index_breakdown");
    }
}

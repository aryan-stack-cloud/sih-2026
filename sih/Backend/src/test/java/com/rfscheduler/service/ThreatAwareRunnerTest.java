package com.rfscheduler.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyBoolean;
import static org.mockito.ArgumentMatchers.anyDouble;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.rfscheduler.ml.MlPeriodicityClient;
import com.rfscheduler.ml.MlSchedulerClient;
import com.rfscheduler.ml.ScanDecision;
import com.rfscheduler.simulation.Scenario;
import com.rfscheduler.simulation.ScenarioLibrary;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;

class ThreatAwareRunnerTest {

    /** Stub ML client: records every state vector, answers with a round-robin sweep. */
    private record StubRun(MlSchedulerClient client, List<Map<String, Object>> states) {
    }

    private static StubRun stubScheduler(int numBands) {
        MlSchedulerClient client = mock(MlSchedulerClient.class);
        List<Map<String, Object>> states = new ArrayList<>();
        AtomicInteger counter = new AtomicInteger();
        when(client.decide(anyString(), any(), anyString(), any(), anyString()))
                .thenAnswer(call -> {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> state = (Map<String, Object>) call.getArgument(1);
                    states.add(state);
                    int band = counter.getAndIncrement() % numBands;
                    return new ScanDecision(band, null, "stub-model", "decision-" + band, true);
                });
        return new StubRun(client, states);
    }

    private static MlPeriodicityClient stubPeriodicity() {
        MlPeriodicityClient periodicity = mock(MlPeriodicityClient.class);
        when(periodicity.predictAll(anyString(), anyInt(), anyDouble()))
                .thenReturn(List.of());
        when(periodicity.step(anyString(), anyList(), anyList(), anyDouble(), anyInt(),
                anyDouble(), anyBoolean())).thenReturn(List.of());
        return periodicity;
    }

    private static SimulationRunner.RunRequest request(boolean threatAware, int steps) {
        Scenario scenario = ScenarioLibrary.byId("A");
        return new SimulationRunner.RunRequest(
                "sim_threat_" + (threatAware ? "on" : "off"), scenario, "bandit", 42, steps,
                null, null, true, threatAware);
    }

    @SuppressWarnings("unchecked")
    private static List<Double> stateWeights(Map<String, Object> state) {
        List<Map<String, Object>> bands = (List<Map<String, Object>>) state.get("bands");
        return bands.stream()
                .map(band -> ((Number) band.get("band_priority_weight")).doubleValue())
                .toList();
    }

    @Test
    void flagOnLiftsDetectedBandsAboveNeutralWithoutExceedingMaxPriority() {
        Scenario scenario = ScenarioLibrary.byId("A");
        StubRun stub = stubScheduler(scenario.bands());
        var runner = new SimulationRunner(stub.client(), stubPeriodicity());

        runner.run(request(true, 120));

        assertThat(stub.states()).isNotEmpty();
        List<Map<String, Object>> later = stub.states().subList(1, stub.states().size());
        assertThat(later.stream()
                .flatMap(state -> stateWeights(state).stream())
                .anyMatch(w -> w > 1.0))
                .as("a detected band keeps a priority weight above 1.0")
                .isTrue();
        assertThat(later.stream()
                .flatMap(state -> stateWeights(state).stream())
                .allMatch(w -> w <= 2.0))
                .as("no weight exceeds the maximum emitter priority")
                .isTrue();
    }

    @Test
    void flagOffKeepsEveryWeightNeutral() {
        Scenario scenario = ScenarioLibrary.byId("A");
        StubRun stub = stubScheduler(scenario.bands());
        var runner = new SimulationRunner(stub.client(), stubPeriodicity());

        var result = runner.run(request(false, 120));

        assertThat(result.steps()).isEqualTo(120);
        assertThat(stub.states()).isNotEmpty();
        assertThat(stub.states().stream()
                .flatMap(state -> stateWeights(state).stream()))
                .allSatisfy(w -> assertThat(w).isEqualTo(1.0));
    }
}

package com.rfscheduler.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyDouble;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.anyList;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.rfscheduler.config.MlProperties;
import com.rfscheduler.ml.MlPeriodicityClient;
import com.rfscheduler.ml.MlSchedulerClient;
import com.rfscheduler.simulation.ScenarioLibrary;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

class NoCompatibleModelFallbackTest {

    @Test
    void oneModelConflictStopsDecideRetriesAndSurfacesReason() {
        RestTemplate rest = mock(RestTemplate.class);
        AtomicInteger decideCalls = new AtomicInteger();
        AtomicInteger learnCalls = new AtomicInteger();
        when(rest.postForObject(anyString(), any(), eq(Map.class))).thenAnswer(call -> {
            String url = call.getArgument(0);
            if (url.endsWith("/decide")) {
                decideCalls.incrementAndGet();
                String body = "{\"error\":{\"code\":\"NO_COMPATIBLE_MODEL\","
                        + "\"message\":\"No model for 16 bands\",\"details\":{}}}";
                throw HttpClientErrorException.create(HttpStatus.CONFLICT, "Conflict",
                        HttpHeaders.EMPTY, body.getBytes(StandardCharsets.UTF_8),
                        StandardCharsets.UTF_8);
            }
            if (url.endsWith("/learn")) {
                learnCalls.incrementAndGet();
            }
            return Map.of();
        });
        var scheduler = new MlSchedulerClient(rest,
                new MlProperties("http://localhost:8500", "http://localhost:8600", 100, 100,
                        true));
        MlPeriodicityClient periodicity = mock(MlPeriodicityClient.class);
        when(periodicity.predictAll(anyString(), anyInt(), anyDouble())).thenReturn(List.of());
        when(periodicity.step(anyString(), anyList(), anyList(), anyDouble(), anyInt(),
                anyDouble(), eq(true))).thenReturn(List.of());
        when(periodicity.step(anyString(), anyList(), anyList(), anyDouble(), anyInt(),
                anyDouble(), eq(false))).thenReturn(List.of());
        var runner = new SimulationRunner(scheduler, periodicity);
        var live = new SimulationService.LiveSimulation("sim_test");
        var request = new SimulationRunner.RunRequest("sim_test", ScenarioLibrary.byId("A"),
                "dqn", 42, 4, null, null);

        var result = runner.run(request, live::record, live);

        assertThat(decideCalls).hasValue(1);
        assertThat(learnCalls).hasValue(0);
        assertThat(result.mlDecisions()).isZero();
        assertThat(result.fallbackDecisions()).isEqualTo(4);
        assertThat(result.servedModelIds()).isEmpty();
        assertThat(result.unavailableReason())
                .isEqualTo("dqn has no trained model for scenario A (16 bands)");
        assertThat(live.snapshot()).containsEntry("unavailable_reason", result.unavailableReason());
    }
}

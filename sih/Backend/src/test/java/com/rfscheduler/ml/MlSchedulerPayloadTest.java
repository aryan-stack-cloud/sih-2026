package com.rfscheduler.ml;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.rfscheduler.config.MlProperties;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

class MlSchedulerPayloadTest {

    @Test
    void decisionIncludesScenarioAndLearningIncludesExecutedOutcomes() {
        RestTemplate rest = mock(RestTemplate.class);
        List<Map<String, Object>> bodies = new ArrayList<>();
        when(rest.postForObject(anyString(), any(), eq(Map.class))).thenAnswer(call -> {
            String path = call.getArgument(0);
            HttpEntity<?> entity = call.getArgument(1);
            @SuppressWarnings("unchecked")
            Map<String, Object> body = (Map<String, Object>) entity.getBody();
            bodies.add(body);
            if (path.endsWith("/decide")) {
                return Map.of("data", Map.of("action", Map.of("next_band", 3),
                        "model_id", "model_B", "decision_id", "decision_1"));
            }
            return Map.of("data", Map.of());
        });
        var client = new MlSchedulerClient(rest,
                new MlProperties("http://localhost:8500", "http://localhost:8600", 100, 100,
                        true));
        Map<String, Object> state = Map.of("bands", List.of());

        var decision = client.decide("sim_test", state, "index", "requested_model", "B");
        client.learn("sim_test", decision.decisionId(), state, decision.nextBand(), null,
                1.0, state, List.of(3, 4), List.of(3));

        assertThat(bodies.get(0)).containsEntry("scenario_id", "B")
                .containsEntry("model_id", "requested_model");
        assertThat(bodies.get(1)).containsEntry("scanned_bands", List.of(3, 4))
                .containsEntry("detected_bands", List.of(3));
    }

    @Test
    void otherConflictStillUsesOrdinaryDegradation() {
        RestTemplate rest = mock(RestTemplate.class);
        when(rest.postForObject(anyString(), any(), eq(Map.class))).thenAnswer(call -> {
            String body = "{\"error\":{\"code\":\"OTHER_CONFLICT\","
                    + "\"message\":\"temporary conflict\"}}";
            throw HttpClientErrorException.create(HttpStatus.CONFLICT, "Conflict",
                    HttpHeaders.EMPTY, body.getBytes(StandardCharsets.UTF_8),
                    StandardCharsets.UTF_8);
        });
        var client = new MlSchedulerClient(rest,
                new MlProperties("http://localhost:8500", "http://localhost:8600", 100, 100,
                        true));
        assertThat(client.decide("sim_test", Map.of("bands", List.of()), "dqn", null, "A"))
                .isNull();
        assertThat(client.isDegraded()).isTrue();
    }
}

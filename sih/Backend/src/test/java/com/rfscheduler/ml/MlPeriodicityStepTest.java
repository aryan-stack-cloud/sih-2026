package com.rfscheduler.ml;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.rfscheduler.config.MlProperties;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpStatus;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.RestTemplate;

class MlPeriodicityStepTest {

    private static final MlProperties PROPS = new MlProperties(
            "http://localhost:8500", "http://localhost:8600", 100, 100, true);

    @Test
    void combinedStepSendsOrderedOutcomesAndReturnsNextPredictions() {
        RestTemplate rest = mock(RestTemplate.class);
        List<String> calls = new ArrayList<>();
        List<Map<String, Object>> bodies = new ArrayList<>();
        when(rest.postForObject(anyString(), any(), eq(Map.class))).thenAnswer(call -> {
            calls.add(call.getArgument(0));
            bodies.add(body(call.getArgument(1)));
            return predictions(0.75);
        });
        MlPeriodicityClient client = new MlPeriodicityClient(rest, PROPS);
        try {
            List<BandPeriodicity> next = client.step("sim_test", List.of(3, 2), List.of(2),
                    4.0, 4, 5.0, true);
            assertThat(calls).hasSize(1);
            assertThat(calls.get(0)).endsWith("/internal/periodicity/step");
            assertThat(bodies.get(0)).containsEntry("simulation_id", "sim_test")
                    .containsEntry("now", 5.0)
                    .containsEntry("band_ids", List.of(0, 1, 2, 3))
                    .containsEntry("outcomes", List.of(
                            Map.of("band_id", 3, "detected", false, "timestamp", 4.0),
                            Map.of("band_id", 2, "detected", true, "timestamp", 4.0)));
            assertThat(next.get(0).phase()).isEqualTo(0.75);
            assertThat(next.get(2).phase()).isZero();
            assertThat(client.isDegraded()).isFalse();

            assertThat(client.step("sim_test", List.of(1), List.of(), 5.0, 4, 6.0, false))
                    .isEmpty();
            assertThat(calls).hasSize(2);
            assertThat(calls.get(1)).endsWith("/internal/periodicity/step");
        } finally {
            client.shutdownUpdateExecutor();
        }
    }

    @Test
    void notFoundFallsBackToOrderedUpdatesThenBatchPrediction() {
        RestTemplate rest = mock(RestTemplate.class);
        List<String> calls = Collections.synchronizedList(new ArrayList<>());
        when(rest.postForObject(anyString(), any(), eq(Map.class))).thenAnswer(call -> {
            String path = call.getArgument(0);
            if (path.endsWith("/step")) {
                calls.add("step");
                throw new HttpClientErrorException(HttpStatus.NOT_FOUND);
            }
            if (path.endsWith("/update")) {
                Map<String, Object> body = body(call.getArgument(1));
                calls.add("update:" + body.get("band_id") + ":" + body.get("detected"));
                return Map.of();
            }
            calls.add("predict");
            return predictions(0.5);
        });
        MlPeriodicityClient client = new MlPeriodicityClient(rest, PROPS);
        try {
            List<BandPeriodicity> next = client.step("sim_test", List.of(3, 2), List.of(2),
                    4.0, 4, 5.0, true);
            assertThat(calls).containsExactly("step", "update:3:false", "update:2:true",
                    "predict");
            assertThat(next.get(0).phase()).isEqualTo(0.5);
            assertThat(client.isDegraded()).isFalse();
        } finally {
            client.shutdownUpdateExecutor();
        }
    }

    @Test
    void otherFailureMarksDegradedWithoutSendingLegacyUpdates() {
        RestTemplate rest = mock(RestTemplate.class);
        List<String> calls = new ArrayList<>();
        when(rest.postForObject(anyString(), any(), eq(Map.class))).thenAnswer(call -> {
            calls.add(call.getArgument(0));
            throw new HttpServerErrorException(HttpStatus.INTERNAL_SERVER_ERROR);
        });
        MlPeriodicityClient client = new MlPeriodicityClient(rest, PROPS);
        try {
            List<BandPeriodicity> next = client.step("sim_test", List.of(3), List.of(3),
                    4.0, 4, 5.0, true);
            assertThat(calls).hasSize(1);
            assertThat(next).allSatisfy(p -> {
                assertThat(p.phase()).isZero();
                assertThat(p.confidence()).isZero();
            });
            assertThat(client.isDegraded()).isTrue();
        } finally {
            client.shutdownUpdateExecutor();
        }
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> body(HttpEntity<?> request) {
        return (Map<String, Object>) request.getBody();
    }

    private static Map<String, Object> predictions(double phase) {
        return Map.of("data", Map.of("predictions", List.of(
                Map.of("band_id", 0, "phase", phase, "confidence", 0.8))));
    }
}

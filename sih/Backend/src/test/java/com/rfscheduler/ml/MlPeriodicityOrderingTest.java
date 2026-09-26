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
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestTemplate;

class MlPeriodicityOrderingTest {

    @Test
    void predictionAndResetFollowQueuedUpdates() {
        RestTemplate rest = mock(RestTemplate.class);
        List<String> calls = new ArrayList<>();
        when(rest.postForObject(anyString(), any(), eq(Map.class))).thenAnswer(call -> {
            String path = call.getArgument(0);
            if (path.endsWith("/update")) {
                calls.add("update");
                return Map.of();
            }
            if (path.endsWith("/batch")) {
                calls.add("predict");
                return Map.of("data", Map.of("predictions", List.of()));
            }
            calls.add("reset");
            return Map.of();
        });
        MlPeriodicityClient client = new MlPeriodicityClient(rest,
                new MlProperties("http://localhost:8500", "http://localhost:8600", 100, 100,
                        true));
        try {
            client.recordDetection("sim_test", 0, 0);
            client.recordMiss("sim_test", 0, 1);
            client.predictAll("sim_test", 1, 2);
            client.recordDetection("sim_test", 0, 2);
            client.reset("sim_test");
            assertThat(calls).containsExactly("update", "update", "predict", "update", "reset");
        } finally {
            client.shutdownUpdateExecutor();
        }
    }
}

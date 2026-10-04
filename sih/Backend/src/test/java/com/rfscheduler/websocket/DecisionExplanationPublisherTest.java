package com.rfscheduler.websocket;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

import com.rfscheduler.service.SimulationRunner;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

class DecisionExplanationPublisherTest {

    private WebSocketHub hub;
    private AtomicLong clock;
    private SimulationEventPublisher publisher;

    @BeforeEach
    void setUp() {
        hub = mock(WebSocketHub.class);
        clock = new AtomicLong(1_000L);
        publisher = new SimulationEventPublisher(hub, clock::get);
    }

    private static SimulationRunner.StepFrame frameWithExtras() {
        return new SimulationRunner.StepFrame(7, 3, List.of(3), List.of(), List.of(),
                List.of(), 1.0, Map.of("C", 1.0), "m", true, "index",
                Map.of("value", 0.5, "information", 0.2));
    }

    private static SimulationRunner.StepFrame frameWithoutExtras() {
        return new SimulationRunner.StepFrame(7, 3, List.of(3), List.of(), List.of(),
                List.of(), 1.0, Map.of("C", 1.0), "m", true);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> scanDecisionPayload() {
        ArgumentCaptor<Map<String, Object>> frameCap =
                (ArgumentCaptor<Map<String, Object>>) (ArgumentCaptor<?>) ArgumentCaptor
                        .forClass(Map.class);
        verify(hub, times(2)).broadcast(anyString(), anyString(), frameCap.capture());
        return frameCap.getAllValues().stream()
                .filter(f -> "scan_decision".equals(f.get("type")))
                .findFirst()
                .orElseThrow();
    }

    private static List<String> payloadKeysInOrder(Map<String, Object> decision) {
        Map<String, Object> payload = new LinkedHashMap<>(decision);
        payload.remove("type");
        payload.remove("simulation_id");
        return new ArrayList<>(payload.keySet());
    }

    @Test
    void frameWithExtrasProducesBothExtraKeysInOrder() {
        publisher.onStep("s1", frameWithExtras());

        Map<String, Object> decision = scanDecisionPayload();
        assertThat(payloadKeysInOrder(decision)).containsExactly("t", "action", "model_id",
                "reward", "reward_terms", "valid_observation", "decision_source",
                "index_breakdown");
        assertThat(decision.get("decision_source")).isEqualTo("index");
        assertThat(decision.get("index_breakdown")).isEqualTo(
                Map.of("value", 0.5, "information", 0.2));
    }

    @Test
    void frameWithoutExtrasContainsNeitherKey() {
        publisher.onStep("s1", frameWithoutExtras());

        Map<String, Object> decision = scanDecisionPayload();
        assertThat(decision).doesNotContainKeys("decision_source", "index_breakdown");
        assertThat(payloadKeysInOrder(decision)).containsExactly("t", "action", "model_id",
                "reward", "reward_terms", "valid_observation");
    }
}

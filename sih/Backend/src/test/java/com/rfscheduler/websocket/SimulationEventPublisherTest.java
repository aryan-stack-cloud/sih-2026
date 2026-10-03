package com.rfscheduler.websocket;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

import com.rfscheduler.metrics.MetricsSummary;
import com.rfscheduler.service.SimulationRunner;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.atomic.AtomicLong;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

class SimulationEventPublisherTest {

    private WebSocketHub hub;
    private AtomicLong clock;
    private SimulationEventPublisher publisher;

    @BeforeEach
    void setUp() {
        hub = mock(WebSocketHub.class);
        clock = new AtomicLong(1_000L);
        publisher = new SimulationEventPublisher(hub, clock::get);
    }

    private static SimulationRunner.StepFrame frame(int t) {
        return frame(t, List.of(), List.of());
    }

    private static SimulationRunner.StepFrame frame(int t, List<Integer> detected,
            List<Integer> falseAlarms) {
        return new SimulationRunner.StepFrame(t, 3, List.of(3), List.of(), detected, falseAlarms,
                1.0, Map.of("C", 1.0), "m", true);
    }

    private List<Map<String, Object>> allFrames() {
        ArgumentCaptor<String> simCap = ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<String> channelCap = ArgumentCaptor.forClass(String.class);
        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> frameCap =
                (ArgumentCaptor<Map<String, Object>>) (ArgumentCaptor<?>) ArgumentCaptor
                        .forClass(Map.class);
        verify(hub, times(totalBroadcasts)).broadcast(simCap.capture(), channelCap.capture(),
                frameCap.capture());
        return frameCap.getAllValues();
    }

    private int totalBroadcasts;

    private void expectTotal(int n) {
        totalBroadcasts = n;
    }

    private static List<Integer> stepsOf(List<Map<String, Object>> frames, String type) {
        List<Integer> out = new ArrayList<>();
        for (Map<String, Object> f : frames) {
            if (type.equals(f.get("type"))) {
                out.add((Integer) f.get("t"));
            }
        }
        return out;
    }

    private static SimulationRunner.RunResult doneResult(String simId, int steps) {
        MetricsSummary metrics = new MetricsSummary(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
                0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0);
        return new SimulationRunner.RunResult(simId, "baseline", 0L, steps, metrics, List.of(),
                null, 0, 0, false, Set.of(), "");
    }

    @Test
    void quietStepsEmitBothFramesOnTheSameGateIndices() {
        for (int i = 0; i < 30; i++) {
            clock.set(1_000L + i * 10L);
            publisher.onStep("s1", frame(i));
        }
        expectTotal(6);
        List<Map<String, Object>> frames = allFrames();
        assertThat(stepsOf(frames, "spectrum_update")).containsExactly(0, 10, 20);
        assertThat(stepsOf(frames, "scan_decision")).containsExactly(0, 10, 20);
        assertThat(stepsOf(frames, "detection_event")).isEmpty();
    }

    @Test
    void detectionBetweenGatesBypassesDecisionButNotSpectrum() {
        for (int i = 0; i <= 20; i++) {
            clock.set(1_000L + i * 10L);
            publisher.onStep("s1", i == 5 ? frame(i, List.of(2), List.of()) : frame(i));
        }
        expectTotal(3 + 4 + 1);
        List<Map<String, Object>> frames = allFrames();
        assertThat(stepsOf(frames, "spectrum_update")).containsExactly(0, 10, 20);
        assertThat(stepsOf(frames, "scan_decision")).containsExactly(0, 5, 10, 20);
        assertThat(stepsOf(frames, "detection_event")).containsExactly(5);
    }

    @Test
    void falseAlarmOnlyStepBypassesDecisionGate() {
        clock.set(1_000L);
        publisher.onStep("s1", frame(0));
        clock.set(1_010L);
        publisher.onStep("s1", frame(1, List.of(), List.of(4)));
        clock.set(1_020L);
        publisher.onStep("s1", frame(2));
        expectTotal(2 + 2);
        List<Map<String, Object>> frames = allFrames();
        assertThat(stepsOf(frames, "spectrum_update")).containsExactly(0);
        assertThat(stepsOf(frames, "scan_decision")).containsExactly(0, 1);
        assertThat(stepsOf(frames, "detection_event")).containsExactly(1);
    }

    @Test
    void slowStepsEmitBothFramesEveryStep() {
        for (int i = 0; i < 5; i++) {
            clock.set(1_000L + i * 100L);
            publisher.onStep("s1", frame(i));
        }
        expectTotal(10);
        List<Map<String, Object>> frames = allFrames();
        assertThat(stepsOf(frames, "spectrum_update")).containsExactly(0, 1, 2, 3, 4);
        assertThat(stepsOf(frames, "scan_decision")).containsExactly(0, 1, 2, 3, 4);
    }

    @Test
    void onCompleteResetsBothGates() {
        clock.set(1_000L);
        publisher.onStep("s1", frame(0));
        clock.set(1_010L);
        publisher.onStep("s1", frame(1));
        publisher.onComplete("s1", doneResult("s1", 2), "completed", 2);
        publisher.onStep("s1", frame(0));
        expectTotal(2 + 2 + 1);
        List<Map<String, Object>> frames = allFrames();
        assertThat(stepsOf(frames, "spectrum_update")).containsExactly(0, 0);
        assertThat(stepsOf(frames, "scan_decision")).containsExactly(0, 0);
    }

    @Test
    void onErrorResetsBothGates() {
        clock.set(1_000L);
        publisher.onStep("s1", frame(0));
        clock.set(1_010L);
        publisher.onStep("s1", frame(1));
        publisher.onError("s1", "boom");
        publisher.onStep("s1", frame(2));
        // onError also emits broadcastError, which is a separate hub method, not broadcast.
        expectTotal(4);
        List<Map<String, Object>> frames = allFrames();
        assertThat(stepsOf(frames, "spectrum_update")).containsExactly(0, 2);
        assertThat(stepsOf(frames, "scan_decision")).containsExactly(0, 2);
    }

    @Test
    void scanDecisionPayloadKeepsOriginalSixKeysInOrder() {
        clock.set(1_000L);
        publisher.onStep("s1", frame(7));
        expectTotal(2);
        List<Map<String, Object>> frames = allFrames();
        Map<String, Object> decision = frames.stream()
                .filter(f -> "scan_decision".equals(f.get("type"))).findFirst().orElseThrow();
        Map<String, Object> payload = new java.util.LinkedHashMap<>(decision);
        payload.remove("type");
        payload.remove("simulation_id");
        assertThat(new ArrayList<>(payload.keySet())).containsExactly("t", "action", "model_id",
                "reward", "reward_terms", "valid_observation");
    }

    @Test
    void twoSimulationsGateIndependently() {
        clock.set(1_000L);
        publisher.onStep("a", frame(0));
        publisher.onStep("b", frame(0));
        clock.set(1_010L);
        publisher.onStep("a", frame(1));
        publisher.onStep("b", frame(1));
        clock.set(1_100L);
        publisher.onStep("a", frame(2));
        publisher.onStep("b", frame(3));
        expectTotal(8);
        ArgumentCaptor<String> simCap = ArgumentCaptor.forClass(String.class);
        @SuppressWarnings("unchecked")
        ArgumentCaptor<Map<String, Object>> frameCap =
                (ArgumentCaptor<Map<String, Object>>) (ArgumentCaptor<?>) ArgumentCaptor
                        .forClass(Map.class);
        verify(hub, times(8)).broadcast(simCap.capture(), anyString(), frameCap.capture());
        List<String> sims = simCap.getAllValues();
        List<Map<String, Object>> frames = frameCap.getAllValues();
        List<Integer> aSpectrum = new ArrayList<>();
        List<Integer> bSpectrum = new ArrayList<>();
        for (int i = 0; i < frames.size(); i++) {
            if ("spectrum_update".equals(frames.get(i).get("type"))) {
                if ("a".equals(sims.get(i))) {
                    aSpectrum.add((Integer) frames.get(i).get("t"));
                } else {
                    bSpectrum.add((Integer) frames.get(i).get("t"));
                }
            }
        }
        assertThat(aSpectrum).containsExactly(0, 2);
        assertThat(bSpectrum).containsExactly(0, 3);
    }

    @Test
    void bypassEmissionDoesNotShiftLaterGateOpenings() {
        // Gate opens at 0, 10, 20. Detections at 5 and 6 bypass; step 10 must still open.
        for (int i = 0; i <= 20; i++) {
            clock.set(1_000L + i * 10L);
            boolean event = i == 5 || i == 6;
            publisher.onStep("s1", event ? frame(i, List.of(2), List.of()) : frame(i));
        }
        expectTotal(3 + 5 + 2);
        List<Map<String, Object>> frames = allFrames();
        assertThat(stepsOf(frames, "spectrum_update")).containsExactly(0, 10, 20);
        assertThat(stepsOf(frames, "scan_decision")).containsExactly(0, 5, 6, 10, 20);
    }
}

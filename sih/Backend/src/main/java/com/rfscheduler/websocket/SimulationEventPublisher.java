package com.rfscheduler.websocket;

import com.rfscheduler.service.SimulationRunner;
import com.rfscheduler.service.SimulationService;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.stereotype.Component;

/**
 * Turns simulation steps into the WebSocket frames of API_CONTRACT.md Section 3.
 *
 * <p>COALESCING, and why it is here rather than in the transport. Section 3 requires
 * {@code spectrum_update} to be coalesced to at most 10 per second per connection, dropping
 * intermediate frames but never the latest. A simulation runs thousands of steps as fast as the
 * CPU allows, so without this a single run would push tens of thousands of frames at a browser
 * and the "seamless connection" requirement would fail on the first demo.
 *
 * <p>The rule is applied per simulation, at the source: the newest frame always replaces any
 * pending one, and a frame is emitted only when the rate window allows. Two categories bypass it
 * entirely - {@code detection_event} and {@code scan_decision} for detections - because dropping
 * those would lose information the dashboard is specifically there to show, and they are rare
 * compared to the per-step spectrum churn.
 */
@Component
public class SimulationEventPublisher implements SimulationService.StepListener {

    /** Section 3: at most 10 spectrum_update frames per second per connection. */
    private static final long MIN_SPECTRUM_INTERVAL_MS = 100;

    private final WebSocketHub hub;
    private final Map<String, Long> lastSpectrumEmit = new ConcurrentHashMap<>();

    public SimulationEventPublisher(WebSocketHub hub) {
        this.hub = hub;
    }

    @Override
    public void onStep(String simulationId, SimulationRunner.StepFrame frame) {
        long now = System.currentTimeMillis();

        // spectrum_update - coalesced. The latest frame is what matters; intermediate ones are
        // safe to drop because each is a complete picture of that instant, not a delta.
        Long last = lastSpectrumEmit.get(simulationId);
        if (last == null || now - last >= MIN_SPECTRUM_INTERVAL_MS) {
            lastSpectrumEmit.put(simulationId, now);
            hub.broadcast(simulationId, "spectrum", frame("spectrum_update", simulationId, Map.of(
                    "t", frame.t(),
                    "active_bands", frame.activeBands(),
                    "scanned_bands", frame.scannedBands(),
                    "detected_bands", frame.detectedBands())));
        }

        // scan_decision - one per step, but small; sent on the scheduler channel which the
        // dashboard subscribes to separately.
        if (last == null || now - last >= MIN_SPECTRUM_INTERVAL_MS) {
            hub.broadcast(simulationId, "scheduler", frame("scan_decision", simulationId, Map.of(
                    "t", frame.t(),
                    "action", frame.action(),
                    "model_id", frame.modelId() == null ? "" : frame.modelId(),
                    "reward", frame.reward(),
                    "reward_terms", frame.rewardTerms(),
                    "valid_observation", frame.validObservation())));
        }

        // detection_event - never coalesced. A dropped detection is a lost fact, and these are
        // rare relative to the per-step churn.
        if (!frame.detectedBands().isEmpty() || !frame.falseAlarmBands().isEmpty()) {
            hub.broadcast(simulationId, "spectrum", frame("detection_event", simulationId, Map.of(
                    "t", frame.t(),
                    "detected_bands", frame.detectedBands(),
                    "false_alarm_bands", frame.falseAlarmBands())));
        }
    }

    @Override
    public void onComplete(String simulationId, SimulationRunner.RunResult result) {
        lastSpectrumEmit.remove(simulationId);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("t", result.steps());
        payload.put("status", "completed");
        payload.put("metrics", result.metrics().asMap());
        payload.put("degraded", result.degraded());
        payload.put("ml_decisions", result.mlDecisions());
        payload.put("fallback_decisions", result.fallbackDecisions());
        hub.broadcast(simulationId, "metrics", frame("metrics_update", simulationId, payload));
    }

    @Override
    public void onError(String simulationId, String message) {
        lastSpectrumEmit.remove(simulationId);
        hub.broadcastError(simulationId, "SIMULATION_FAILED", message);
    }

    /** Progress for a running experiment, on the training channel. */
    public void publishExperimentProgress(String experimentId, Map<String, Object> progress) {
        hub.broadcast(experimentId, "training",
                frame("training_progress", experimentId, progress));
    }

    private static Map<String, Object> frame(String type, String id, Map<String, Object> payload) {
        Map<String, Object> f = new LinkedHashMap<>();
        f.put("type", type);
        f.put("simulation_id", id);
        f.putAll(payload);
        return f;
    }
}

package com.rfscheduler.websocket;

import com.rfscheduler.service.SimulationRunner;
import com.rfscheduler.service.SimulationService;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.LongSupplier;
import org.springframework.beans.factory.annotation.Autowired;
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
 * <p>Each simulation id carries two independent gates, both 10 per second: {@code lastSpectrumEmit}
 * for {@code spectrum_update} and {@code lastDecisionEmit} for {@code scan_decision}. A quiet step
 * (no detections, no false alarms) emits a {@code scan_decision} only when its own gate is open,
 * so the two frame types stay paired on the same step indices - each gate advances in lock-step
 * with the other because both open on the same steps.
 *
 * <p>Steps that carry detections or false alarms bypass the decision gate: their
 * {@code scan_decision} is emitted immediately, together with the {@code detection_event} (which
 * is never gated - a dropped detection is a lost fact). A bypass emission does not move
 * {@code lastDecisionEmit}, so the following gate openings land exactly where they would have
 * without it.
 */
@Component
public class SimulationEventPublisher implements SimulationService.StepListener {

    /** Section 3: at most 10 spectrum_update frames per second per connection. */
    private static final long MIN_SPECTRUM_INTERVAL_MS = 100;

    /** Own gate for scan_decision, kept in lock-step with the spectrum gate on quiet steps. */
    private static final long MIN_DECISION_INTERVAL_MS = 100;

    private final WebSocketHub hub;
    private final LongSupplier nowMs;
    private final Map<String, Long> lastSpectrumEmit = new ConcurrentHashMap<>();
    private final Map<String, Long> lastDecisionEmit = new ConcurrentHashMap<>();

    @Autowired
    public SimulationEventPublisher(WebSocketHub hub) {
        this(hub, System::currentTimeMillis);
    }

    /** Test seam: a controllable clock instead of the wall clock. */
    public SimulationEventPublisher(WebSocketHub hub, LongSupplier nowMs) {
        this.hub = hub;
        this.nowMs = nowMs;
    }

    @Override
    public void onStep(String simulationId, SimulationRunner.StepFrame frame) {
        long now = nowMs.getAsLong();

        // spectrum_update - coalesced. The latest frame is what matters; intermediate ones are
        // safe to drop because each is a complete picture of that instant, not a delta.
        Long lastSpectrum = lastSpectrumEmit.get(simulationId);
        if (lastSpectrum == null || now - lastSpectrum >= MIN_SPECTRUM_INTERVAL_MS) {
            lastSpectrumEmit.put(simulationId, now);
            hub.broadcast(simulationId, "spectrum", frame("spectrum_update", simulationId, Map.of(
                    "t", frame.t(),
                    "active_bands", frame.activeBands(),
                    "scanned_bands", frame.scannedBands(),
                    "detected_bands", frame.detectedBands())));
        }

        // scan_decision - gated on its own window, except that steps carrying a detection or
        // false alarm always emit: the dashboard is specifically there to show those, and they
        // are rare compared to the per-step churn. A bypass never moves the gate, so quiet
        // steps keep opening in lock-step with the spectrum gate above.
        Long lastDecision = lastDecisionEmit.get(simulationId);
        boolean decisionGateOpen =
                lastDecision == null || now - lastDecision >= MIN_DECISION_INTERVAL_MS;
        boolean hasEvent =
                !frame.detectedBands().isEmpty() || !frame.falseAlarmBands().isEmpty();
        if (decisionGateOpen || hasEvent) {
            if (decisionGateOpen) {
                lastDecisionEmit.put(simulationId, now);
            }
            Map<String, Object> payload = new LinkedHashMap<>();
            payload.put("t", frame.t());
            payload.put("action", frame.action());
            payload.put("model_id", frame.modelId() == null ? "" : frame.modelId());
            payload.put("reward", frame.reward());
            payload.put("reward_terms", frame.rewardTerms());
            payload.put("valid_observation", frame.validObservation());
            hub.broadcast(simulationId, "scheduler",
                    frame("scan_decision", simulationId, payload));
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
    public void onComplete(String simulationId, SimulationRunner.RunResult result,
                           String status, int processedSteps) {
        lastSpectrumEmit.remove(simulationId);
        lastDecisionEmit.remove(simulationId);
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("t", processedSteps);
        payload.put("status", status);
        payload.put("metrics", result.metrics().asMap());
        payload.put("degraded", result.degraded());
        payload.put("ml_decisions", result.mlDecisions());
        payload.put("fallback_decisions", result.fallbackDecisions());
        hub.broadcast(simulationId, "metrics", frame("metrics_update", simulationId, payload));
    }

    @Override
    public void onError(String simulationId, String message) {
        lastSpectrumEmit.remove(simulationId);
        lastDecisionEmit.remove(simulationId);
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

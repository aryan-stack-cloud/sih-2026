package com.rfscheduler.ml;

import com.rfscheduler.config.MlProperties;
import java.util.LinkedHashMap;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

/**
 * HTTP client for Ai-ml-1, the scan-decision policy service (API_CONTRACT.md Section 4).
 *
 * <p>The Backend is the only service that calls this one. Every request carries the full
 * StateVector, so Ai-ml-1 needs no simulation state of its own - except the online-learning
 * session it keeps per {@code simulation_id}, which is why {@link #reset} exists.
 *
 * <p>DEGRADATION. If Ai-ml-1 is unreachable the scheduler falls back to round-robin rather than
 * failing the simulation, controlled by {@code rfscheduler.ml.fallback-to-baseline}. That is the
 * right default for a demo - a dropped ML service becomes visibly worse scan behaviour instead of
 * a dead run - but it must be visible, so every fallback is logged and the decision is tagged
 * {@code fromMl=false} so the metrics can tell the two apart.
 */
@Component
public class MlSchedulerClient {

    private static final Logger log = LoggerFactory.getLogger(MlSchedulerClient.class);

    private final RestTemplate rest;
    private final MlProperties props;

    private volatile boolean degraded;

    public MlSchedulerClient(RestTemplate mlRestTemplate, MlProperties props) {
        this.rest = mlRestTemplate;
        this.props = props;
    }

    public boolean isDegraded() {
        return degraded;
    }

    public boolean healthy() {
        try {
            Map<?, ?> body = rest.getForObject(
                    props.schedulerUrl() + "/internal/health", Map.class);
            return body != null && Boolean.TRUE.equals(body.get("success"));
        } catch (RuntimeException e) {
            return false;
        }
    }

    /**
     * {@code POST /internal/decide}. Returns null when the service is unreachable, so the caller
     * can apply its fallback rather than this client inventing a decision.
     */
    @SuppressWarnings("unchecked")
    public ScanDecision decide(
            String simulationId, Map<String, Object> stateVector, String policy, String modelId) {

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("simulation_id", simulationId);
        body.put("state", stateVector);
        body.put("policy", policy);
        if (modelId != null) {
            body.put("model_id", modelId);
        }

        try {
            Map<String, Object> response = post("/internal/decide", body, simulationId);
            Map<String, Object> data = (Map<String, Object>) response.get("data");
            Map<String, Object> action = (Map<String, Object>) data.get("action");

            Object dwell = action.get("dwell_time");
            degraded = false;
            return new ScanDecision(
                    ((Number) action.get("next_band")).intValue(),
                    dwell instanceof Number n ? n.intValue() : null,
                    (String) data.get("model_id"),
                    (String) data.get("decision_id"),
                    true);
        } catch (RuntimeException e) {
            markDegraded("decide", simulationId, e);
            return null;
        }
    }

    /**
     * {@code POST /internal/learn}. The reward is computed here, by the Backend, and consumed
     * there - Ai-ml-1 never recomputes Equation 10.1.
     *
     * <p>Failures are swallowed deliberately: a lost learning update degrades the policy slightly,
     * whereas aborting the simulation step loses the run. The degraded flag surfaces it.
     */
    public boolean learn(
            String simulationId,
            String decisionId,
            Map<String, Object> state,
            int actionBand,
            Integer dwellTime,
            double reward,
            Map<String, Object> nextState) {

        if (decisionId == null) {
            return false;   // the decision came from the local fallback; nothing to teach
        }

        Map<String, Object> action = new LinkedHashMap<>();
        action.put("next_band", actionBand);
        if (dwellTime != null) {
            action.put("dwell_time", dwellTime);
        }

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("simulation_id", simulationId);
        body.put("decision_id", decisionId);
        body.put("state", state);
        body.put("action", action);
        body.put("reward", reward);
        if (nextState != null) {
            body.put("next_state", nextState);
        }

        try {
            post("/internal/learn", body, simulationId);
            return true;
        } catch (RuntimeException e) {
            markDegraded("learn", simulationId, e);
            return false;
        }
    }

    /**
     * {@code POST /internal/reset}. Must be called on simulation reset, alongside Ai-ml-2's
     * {@code /internal/periodicity/reset}, or the next run of this simulation id inherits the
     * previous run's learned beliefs.
     */
    public boolean reset(String simulationId) {
        try {
            post("/internal/reset", Map.of("simulation_id", simulationId), simulationId);
            return true;
        } catch (RuntimeException e) {
            markDegraded("reset", simulationId, e);
            return false;
        }
    }

    /** {@code POST /internal/train} - proxied by the Backend's /api/v1/models/train. */
    @SuppressWarnings("unchecked")
    public Map<String, Object> train(Map<String, Object> request) {
        Map<String, Object> response = post("/internal/train", request, null);
        return (Map<String, Object>) response.get("data");
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> trainStatus(String jobId) {
        Map<String, Object> response = get("/internal/train/" + jobId + "/status");
        return (Map<String, Object>) response.get("data");
    }

    @SuppressWarnings("unchecked")
    public Object listModels(String algorithm, Boolean active) {
        StringBuilder path = new StringBuilder("/internal/models");
        StringBuilder query = new StringBuilder();
        if (algorithm != null) {
            query.append("algorithm=").append(algorithm);
        }
        if (active != null) {
            if (query.length() > 0) {
                query.append("&");
            }
            query.append("active=").append(active);
        }
        if (query.length() > 0) {
            path.append("?").append(query);
        }
        return ((Map<String, Object>) get(path.toString())).get("data");
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> getModel(String modelId) {
        return (Map<String, Object>) get("/internal/models/" + modelId).get("data");
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> activateModel(String modelId) {
        return (Map<String, Object>) post(
                "/internal/models/" + modelId + "/activate", Map.of(), null).get("data");
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> evaluateModel(String modelId, Map<String, Object> request) {
        return (Map<String, Object>) post(
                "/internal/models/" + modelId + "/evaluate", request, null).get("data");
    }

    // -- plumbing ---------------------------------------------------------------------------

    @SuppressWarnings("unchecked")
    private Map<String, Object> post(String path, Object body, String simulationId) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        if (simulationId != null) {
            // Correlation-ID passthrough (NFR-008): one simulation traceable across the hop.
            headers.set("X-Simulation-Id", simulationId);
        }
        return rest.postForObject(
                props.schedulerUrl() + path, new HttpEntity<>(body, headers), Map.class);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> get(String path) {
        return rest.getForObject(props.schedulerUrl() + path, Map.class);
    }

    private void markDegraded(String operation, String simulationId, RuntimeException e) {
        if (!degraded) {
            log.warn("Ai-ml-1 {} failed, degrading to local policy: {}", operation, e.toString());
        }
        degraded = true;
    }
}

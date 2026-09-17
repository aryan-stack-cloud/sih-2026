package com.rfscheduler.ml;

import com.rfscheduler.config.MlProperties;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;

/**
 * HTTP client for Ai-ml-2, the periodicity estimator (API_CONTRACT.md Section 5).
 *
 * <p>WHY THE BATCH CALL. The StateBuilder needs a prediction for every band before every
 * scheduler decision. Looping the single-band GET costs one HTTP round trip per band: measured at
 * 64 bands that is ~181 ms per simulation step, against NFR-002's 50 ms budget for the whole
 * decision - and the estimator's own work in that measurement was 0.13 ms. It was all round-trip
 * overhead. {@code /internal/periodicity/predict/batch} collapses it to a single call at ~3 ms.
 *
 * <p>DEGRADATION. If Ai-ml-2 is unreachable, every band comes back as "no claim" and the two
 * periodicity features stay at zero. Ai-ml-1 reads that as no information, which is correct: the
 * scheduler loses a signal but is not fed a wrong one.
 */
@Component
public class MlPeriodicityClient {

    private static final Logger log = LoggerFactory.getLogger(MlPeriodicityClient.class);

    private final RestTemplate rest;
    private final MlProperties props;

    private volatile boolean degraded;

    public MlPeriodicityClient(RestTemplate mlRestTemplate, MlProperties props) {
        this.rest = mlRestTemplate;
        this.props = props;
    }

    public boolean isDegraded() {
        return degraded;
    }

    public boolean healthy() {
        try {
            Map<?, ?> body = rest.getForObject(
                    props.periodicityUrl() + "/internal/health", Map.class);
            return body != null && Boolean.TRUE.equals(body.get("success"));
        } catch (RuntimeException e) {
            return false;
        }
    }

    /**
     * {@code POST /internal/periodicity/update} - called on every confirmed detection.
     *
     * <p>Fire-and-forget by design: a lost update slightly weakens a future estimate, whereas
     * failing the simulation step loses the run.
     */
    public void recordDetection(String simulationId, int bandId, double detectionTimestamp) {
        recordScan(simulationId, bandId, detectionTimestamp, true);
    }

    /**
     * {@code POST /internal/periodicity/update} with {@code detected=false} - called on every
     * scanned band that did NOT produce a detection this step (API_CONTRACT.md Section 5,
     * "detected: false").
     *
     * <p>This is the fix for the gap RUNNING.md documents: without it, Ai-ml-2 only ever learns
     * about the steps a band lit up, never the far more numerous steps it was looked at and
     * found quiet, so it cannot tell "this band is quiet" from "this band was never looked at".
     * Fire-and-forget, same rationale as {@link #recordDetection}.
     */
    public void recordMiss(String simulationId, int bandId, double timestamp) {
        recordScan(simulationId, bandId, timestamp, false);
    }

    private void recordScan(String simulationId, int bandId, double timestamp, boolean detected) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("simulation_id", simulationId);
        body.put("band_id", bandId);
        body.put("detection_timestamp", timestamp);
        body.put("detected", detected);
        try {
            post("/internal/periodicity/update", body, simulationId);
            degraded = false;
        } catch (RuntimeException e) {
            markDegraded("update", e);
        }
    }

    /**
     * {@code POST /internal/periodicity/predict/batch} - every band in one round trip.
     *
     * <p>Always returns one entry per requested band; unreachable service or unseen band both
     * yield {@link BandPeriodicity#none}, never a gap in the list.
     */
    @SuppressWarnings("unchecked")
    public List<BandPeriodicity> predictAll(String simulationId, int numBands, double now) {
        List<Integer> bandIds = new ArrayList<>(numBands);
        for (int b = 0; b < numBands; b++) {
            bandIds.add(b);
        }

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("simulation_id", simulationId);
        body.put("band_ids", bandIds);
        body.put("now", now);

        try {
            Map<String, Object> response =
                    post("/internal/periodicity/predict/batch", body, simulationId);
            Map<String, Object> data = (Map<String, Object>) response.get("data");
            List<Map<String, Object>> predictions =
                    (List<Map<String, Object>>) data.get("predictions");

            List<BandPeriodicity> out = new ArrayList<>(numBands);
            for (int b = 0; b < numBands; b++) {
                out.add(BandPeriodicity.none(b));
            }
            for (Map<String, Object> p : predictions) {
                int bandId = ((Number) p.get("band_id")).intValue();
                if (bandId < 0 || bandId >= numBands) {
                    continue;
                }
                Map<String, Object> window =
                        (Map<String, Object>) p.get("predicted_next_active_window");
                out.set(bandId, new BandPeriodicity(
                        bandId,
                        asDouble(p.get("estimated_period")),
                        window == null ? null : asDouble(window.get("start")),
                        window == null ? null : asDouble(window.get("end")),
                        asDouble(p.get("confidence")) == null ? 0.0 : asDouble(p.get("confidence")),
                        asDouble(p.get("phase")) == null ? 0.0 : asDouble(p.get("phase"))));
            }
            degraded = false;
            return out;
        } catch (RuntimeException e) {
            markDegraded("predict/batch", e);
            List<BandPeriodicity> fallback = new ArrayList<>(numBands);
            for (int b = 0; b < numBands; b++) {
                fallback.add(BandPeriodicity.none(b));
            }
            return fallback;
        }
    }

    /** {@code POST /internal/periodicity/reset} - called on simulation reset. */
    public boolean reset(String simulationId) {
        try {
            post("/internal/periodicity/reset", Map.of("simulation_id", simulationId), simulationId);
            return true;
        } catch (RuntimeException e) {
            markDegraded("reset", e);
            return false;
        }
    }

    /** {@code GET /internal/periodicity/state} - debugging passthrough. */
    @SuppressWarnings("unchecked")
    public Map<String, Object> state(String simulationId, int bandId) {
        Map<String, Object> response = rest.getForObject(
                props.periodicityUrl() + "/internal/periodicity/state?simulation_id="
                        + simulationId + "&band_id=" + bandId, Map.class);
        return response == null ? Map.of() : (Map<String, Object>) response.get("data");
    }

    // -- plumbing ---------------------------------------------------------------------------

    @SuppressWarnings("unchecked")
    private Map<String, Object> post(String path, Object body, String simulationId) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        if (simulationId != null) {
            headers.set("X-Simulation-Id", simulationId);
        }
        return rest.postForObject(
                props.periodicityUrl() + path, new HttpEntity<>(body, headers), Map.class);
    }

    private static Double asDouble(Object value) {
        return value instanceof Number n ? n.doubleValue() : null;
    }

    private void markDegraded(String operation, RuntimeException e) {
        if (!degraded) {
            log.warn("Ai-ml-2 {} failed, periodicity features will be zero: {}",
                    operation, e.toString());
        }
        degraded = true;
    }
}

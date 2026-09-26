package com.rfscheduler.ml;

import com.rfscheduler.config.MlProperties;
import jakarta.annotation.PreDestroy;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.HashSet;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestTemplate;

/**
 * HTTP client for Ai-ml-2, the periodicity estimator (API_CONTRACT.md Section 5).
 *
 * <p>The first decision uses batch prediction. Subsequent steps combine scan outcomes and the next
 * prediction in one ordered {@code /internal/periodicity/step} call. Older Ai-ml-2 versions fall
 * back to per-band updates followed by batch prediction.
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

    // Compatibility path only: a single worker preserves per-band update order when /step is 404.
    private final ExecutorService updateExecutor = Executors.newSingleThreadExecutor(r -> {
        Thread t = new Thread(r, "periodicity-update");
        t.setDaemon(true);
        return t;
    });
    private final Map<String, Future<?>> pendingUpdates = new ConcurrentHashMap<>();

    public MlPeriodicityClient(RestTemplate mlRestTemplate, MlProperties props) {
        this.rest = mlRestTemplate;
        this.props = props;
    }

    public boolean isDegraded() {
        return degraded;
    }

    @PreDestroy
    void shutdownUpdateExecutor() {
        updateExecutor.shutdown();
        try {
            if (!updateExecutor.awaitTermination(5, TimeUnit.SECONDS)) {
                updateExecutor.shutdownNow();
            }
        } catch (InterruptedException e) {
            updateExecutor.shutdownNow();
            Thread.currentThread().interrupt();
        }
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
     * {@code POST /internal/periodicity/update} - compatibility path for older Ai-ml-2.
     *
     * <p>Fire-and-forget by design: a lost update slightly weakens a future estimate, whereas
     * failing the simulation step loses the run.
     */
    public void recordDetection(String simulationId, int bandId, double detectionTimestamp) {
        recordScan(simulationId, bandId, detectionTimestamp, true);
    }

    /**
     * {@code POST /internal/periodicity/update} with {@code detected=false} in compatibility mode.
     *
     * <p>Both hits and misses must reach the estimator; an unscanned band is different from a quiet
     * scanned band. Fire-and-forget, same rationale as {@link #recordDetection}.
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
        // Dispatch and return immediately - see the field doc on updateExecutor. The caller (the
        // simulation step loop) must not wait on Ai-ml-2's response to move on to the next step.
        Future<?> pending = updateExecutor.submit(() -> {
            try {
                post("/internal/periodicity/update", body, simulationId);
                degraded = false;
            } catch (RuntimeException e) {
                markDegraded("update", e);
            }
        });
        pendingUpdates.put(simulationId, pending);
    }

    /** Drain this simulation's queued updates before predicting or clearing its estimator. */
    private void awaitPending(String simulationId) {
        Future<?> pending = pendingUpdates.get(simulationId);
        if (pending == null) {
            return;
        }
        try {
            pending.get();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new IllegalStateException("interrupted waiting for periodicity updates", e);
        } catch (java.util.concurrent.ExecutionException e) {
            markDegraded("update", new IllegalStateException(e.getCause()));
        } finally {
            pendingUpdates.remove(simulationId, pending);
        }
    }

    /** Apply one scan's outcomes, then predict the next state in one ordered round trip. */
    public List<BandPeriodicity> step(String simulationId, List<Integer> scannedBands,
                                     List<Integer> detectedBands, double timestamp,
                                     int numBands, double now, boolean predictionsNeeded) {
        // Only the compatibility path can leave queued updates for this simulation.
        awaitPending(simulationId);
        Set<Integer> detected = new HashSet<>(detectedBands);
        List<Map<String, Object>> outcomes = new ArrayList<>(scannedBands.size());
        for (int band : scannedBands) {
            outcomes.add(Map.of("band_id", band, "detected", detected.contains(band),
                    "timestamp", timestamp));
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("simulation_id", simulationId);
        body.put("outcomes", outcomes);
        body.put("now", now);
        body.put("band_ids", bandIds(numBands));
        try {
            Map<String, Object> response = post("/internal/periodicity/step", body, simulationId);
            List<BandPeriodicity> predictions = predictionsNeeded
                    ? parsePredictions(response, numBands) : List.of();
            degraded = false;
            return predictions;
        } catch (HttpClientErrorException e) {
            if (e.getStatusCode().value() == 404) {
                // Older Ai-ml-2: preserve ordered updates and the existing batch prediction.
                for (int band : scannedBands) {
                    recordScan(simulationId, band, timestamp, detected.contains(band));
                }
                if (predictionsNeeded) {
                    return predictAll(simulationId, numBands, now);
                }
                awaitPending(simulationId);
                return List.of();
            }
            markDegraded("step", e);
            return predictionsNeeded ? noPredictions(numBands) : List.of();
        } catch (RuntimeException e) {
            markDegraded("step", e);
            return predictionsNeeded ? noPredictions(numBands) : List.of();
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
        awaitPending(simulationId);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("simulation_id", simulationId);
        body.put("band_ids", bandIds(numBands));
        body.put("now", now);

        try {
            Map<String, Object> response =
                    post("/internal/periodicity/predict/batch", body, simulationId);
            List<BandPeriodicity> out = parsePredictions(response, numBands);
            degraded = false;
            return out;
        } catch (RuntimeException e) {
            markDegraded("predict/batch", e);
            return noPredictions(numBands);
        }
    }

    private static List<Integer> bandIds(int numBands) {
        List<Integer> ids = new ArrayList<>(numBands);
        for (int b = 0; b < numBands; b++) {
            ids.add(b);
        }
        return ids;
    }

    private static List<BandPeriodicity> noPredictions(int numBands) {
        List<BandPeriodicity> out = new ArrayList<>(numBands);
        for (int b = 0; b < numBands; b++) {
            out.add(BandPeriodicity.none(b));
        }
        return out;
    }

    @SuppressWarnings("unchecked")
    private static List<BandPeriodicity> parsePredictions(Map<String, Object> response,
                                                           int numBands) {
        Map<String, Object> data = (Map<String, Object>) response.get("data");
        List<Map<String, Object>> predictions =
                (List<Map<String, Object>>) data.get("predictions");
        List<BandPeriodicity> out = noPredictions(numBands);
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
        return out;
    }

    /** {@code POST /internal/periodicity/reset} - called on simulation reset. */
    public boolean reset(String simulationId) {
        try {
            awaitPending(simulationId);
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

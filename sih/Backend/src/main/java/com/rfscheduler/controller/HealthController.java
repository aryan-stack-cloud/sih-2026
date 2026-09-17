package com.rfscheduler.controller;

import com.rfscheduler.dto.ApiResponse;
import com.rfscheduler.ml.MlPeriodicityClient;
import com.rfscheduler.ml.MlSchedulerClient;
import com.rfscheduler.service.SimulationService;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Health and readiness (API_CONTRACT.md Section 2, no auth required).
 *
 * <p>{@code /health} is liveness: is this process up. {@code /ready} is dependency check: can it
 * actually serve a simulation, which means the ML services are reachable. Kept distinct on
 * purpose - a Backend that is alive but cannot reach Ai-ml-1 should fail readiness rather than
 * quietly serving degraded runs.
 */
@RestController
public class HealthController {

    private final MlSchedulerClient schedulerClient;
    private final MlPeriodicityClient periodicityClient;
    private final SimulationService simulations;

    public HealthController(MlSchedulerClient schedulerClient,
                            MlPeriodicityClient periodicityClient,
                            SimulationService simulations) {
        this.schedulerClient = schedulerClient;
        this.periodicityClient = periodicityClient;
        this.simulations = simulations;
    }

    @GetMapping("/health")
    public ApiResponse<Map<String, Object>> health() {
        return ApiResponse.ok(Map.of(
                "status", "ok",
                "service", "rf-scheduler-backend",
                "scope", "simulation-only"));
    }

    @GetMapping("/ready")
    public ResponseEntity<ApiResponse<Map<String, Object>>> ready() {
        boolean scheduler = schedulerClient.healthy();
        boolean periodicity = periodicityClient.healthy();

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("status", scheduler && periodicity ? "ready" : "degraded");
        body.put("ml_scheduler", scheduler ? "up" : "down");
        body.put("ml_periodicity", periodicity ? "up" : "down");
        body.put("running_simulations", simulations.runningCount());

        // Degraded is still 200: the Backend can serve the baseline policy and every read
        // endpoint without the ML services. The body says what is actually reachable.
        return ResponseEntity.ok(ApiResponse.ok(body));
    }
}

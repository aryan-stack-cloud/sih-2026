package com.rfscheduler.controller;

import com.rfscheduler.dto.ApiResponse;
import com.rfscheduler.exception.ApiException;
import com.rfscheduler.experiments.ExperimentService;
import com.rfscheduler.service.SimulationService;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** Metrics reads - API_CONTRACT.md Section 2. */
@RestController
@RequestMapping("/api/v1/metrics")
public class MetricsController {

    private final SimulationService simulations;
    private final ExperimentService experiments;

    public MetricsController(SimulationService simulations, ExperimentService experiments) {
        this.simulations = simulations;
        this.experiments = experiments;
    }

    /**
     * Live metrics for a running simulation.
     *
     * <p>The contract calls this the polling fallback for the WebSocket, so it must work for a
     * client that never opens a socket at all - same snapshot the WS reconnect replay sends.
     */
    @GetMapping("/live")
    public ApiResponse<Map<String, Object>> live(@RequestParam String simulationId) {
        return ApiResponse.ok(simulations.liveState(simulationId).snapshot());
    }

    @GetMapping("/{experimentId}")
    public ApiResponse<Map<String, Object>> forExperiment(@PathVariable String experimentId) {
        return ApiResponse.ok(experiments.results(experimentId));
    }

    /** Compares two or more completed experiments side by side. */
    @GetMapping("/compare")
    public ApiResponse<Map<String, Object>> compare(@RequestParam("ids") List<String> ids) {
        if (ids == null || ids.size() < 2) {
            throw ApiException.validation("at least two experiment ids are required",
                    Map.of("ids", "expected 2 or more"));
        }
        Map<String, Object> byExperiment = new LinkedHashMap<>();
        List<String> missing = new ArrayList<>();
        for (String id : ids) {
            try {
                byExperiment.put(id, experiments.results(id));
            } catch (ApiException e) {
                missing.add(id);
            }
        }
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("experiments", byExperiment);
        if (!missing.isEmpty()) {
            // Reported rather than thrown: comparing the ones that are ready is more useful than
            // failing the whole call because one is still running.
            body.put("unavailable", missing);
        }
        return ApiResponse.ok(body);
    }
}

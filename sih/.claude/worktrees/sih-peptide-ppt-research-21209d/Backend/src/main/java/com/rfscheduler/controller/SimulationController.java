package com.rfscheduler.controller;

import com.rfscheduler.domain.SimulationEntity;
import com.rfscheduler.dto.ApiResponse;
import com.rfscheduler.dto.Requests;
import com.rfscheduler.service.SimulationService;
import com.rfscheduler.websocket.SimulationEventPublisher;
import jakarta.validation.Valid;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** Simulation CRUD and lifecycle - API_CONTRACT.md Section 2. */
@RestController
@RequestMapping("/api/v1/simulations")
public class SimulationController {

    private final SimulationService simulations;
    private final SimulationEventPublisher events;

    public SimulationController(SimulationService simulations, SimulationEventPublisher events) {
        this.simulations = simulations;
        this.events = events;
    }

    @PostMapping
    public ResponseEntity<ApiResponse<Map<String, Object>>> create(
            @Valid @RequestBody Requests.CreateSimulation body) {
        SimulationEntity sim = simulations.create(body.name(), body.bands(), body.durationSteps(),
                body.seed(), body.scenario(), body.policy());
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.ok(summary(sim)));
    }

    @GetMapping
    public ApiResponse<Map<String, Object>> list(
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Page<SimulationEntity> found =
                simulations.list(status, PageRequest.of(Math.max(0, page), Math.min(size, 200)));
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("items", found.getContent().stream().map(SimulationController::summary).toList());
        body.put("page", found.getNumber());
        body.put("size", found.getSize());
        body.put("total", found.getTotalElements());
        return ApiResponse.ok(body);
    }

    @GetMapping("/{id}")
    public ApiResponse<Map<String, Object>> get(@PathVariable String id) {
        return ApiResponse.ok(detail(simulations.get(id)));
    }

    @PutMapping("/{id}")
    public ApiResponse<Map<String, Object>> update(
            @PathVariable String id, @Valid @RequestBody Requests.UpdateSimulation body) {
        return ApiResponse.ok(summary(simulations.update(id, body.name(), body.bands(),
                body.durationSteps(), body.seed(), body.policy())));
    }

    @DeleteMapping("/{id}")
    public ApiResponse<Map<String, Object>> delete(@PathVariable String id) {
        simulations.delete(id);
        return ApiResponse.ok(Map.of("id", id, "deleted", true));
    }

    @PostMapping("/{id}/start")
    public ApiResponse<Map<String, Object>> start(@PathVariable String id) {
        return ApiResponse.ok(summary(simulations.start(id, events)));
    }

    @PostMapping("/{id}/stop")
    public ApiResponse<Map<String, Object>> stop(@PathVariable String id) {
        return ApiResponse.ok(summary(simulations.stop(id)));
    }

    @PostMapping("/{id}/reset")
    public ApiResponse<Map<String, Object>> reset(@PathVariable String id) {
        return ApiResponse.ok(summary(simulations.reset(id)));
    }

    static Map<String, Object> summary(SimulationEntity sim) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", sim.getId());
        m.put("name", sim.getName());
        m.put("status", sim.getStatus());
        m.put("bands", sim.getBands());
        m.put("duration_steps", sim.getDurationSteps());
        m.put("current_step", sim.getCurrentStep());
        m.put("seed", sim.getSeed());
        m.put("policy_type", sim.getPolicyType());
        m.put("scenario_id", sim.getScenarioId());
        m.put("created_at", sim.getCreatedAt());
        return m;
    }

    private Map<String, Object> detail(SimulationEntity sim) {
        Map<String, Object> m = summary(sim);
        var live = simulations.liveStateOrNull(sim.getId());
        if (live != null) {
            m.put("live", live.snapshot());
        }
        return m;
    }
}

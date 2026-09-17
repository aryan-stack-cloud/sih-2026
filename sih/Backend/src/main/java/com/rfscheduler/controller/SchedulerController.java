package com.rfscheduler.controller;

import com.rfscheduler.dto.ApiResponse;
import com.rfscheduler.dto.Requests;
import com.rfscheduler.ml.MlPeriodicityClient;
import com.rfscheduler.ml.MlSchedulerClient;
import com.rfscheduler.service.SimulationService;
import com.rfscheduler.simulation.ScenarioLibrary;
import jakarta.validation.Valid;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * Scheduler status and policy selection - API_CONTRACT.md Section 2.
 *
 * <p>Policy is a property of the simulation, so {@code PUT /scheduler/config} updates the named
 * simulation rather than a global. A single global "current policy" would make two concurrent
 * simulations silently fight over it, and NFR-004 requires at least five at once.
 */
@RestController
@RequestMapping("/api/v1/scheduler")
public class SchedulerController {

    private final SimulationService simulations;
    private final MlSchedulerClient scheduler;
    private final MlPeriodicityClient periodicity;

    public SchedulerController(SimulationService simulations, MlSchedulerClient scheduler,
                               MlPeriodicityClient periodicity) {
        this.simulations = simulations;
        this.scheduler = scheduler;
        this.periodicity = periodicity;
    }

    @GetMapping("/status")
    public ApiResponse<Map<String, Object>> status(@RequestParam String simulationId) {
        var sim = simulations.get(simulationId);
        var live = simulations.liveStateOrNull(simulationId);

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("simulation_id", simulationId);
        body.put("policy", sim.getPolicyType());
        body.put("status", sim.getStatus());
        body.put("step_count", live == null ? sim.getCurrentStep() : live.currentStep());
        body.put("ml_scheduler_degraded", scheduler.isDegraded());
        body.put("ml_periodicity_degraded", periodicity.isDegraded());
        body.put("available_policies",
                List.of("baseline", "random", "bandit", "q_learning", "dqn", "ppo"));
        return ApiResponse.ok(body);
    }

    @PutMapping("/config")
    public ApiResponse<Map<String, Object>> configure(
            @RequestParam String simulationId,
            @Valid @RequestBody Requests.SchedulerConfigRequest body) {
        var sim = simulations.update(simulationId, null, null, null, null, body.policy());
        return ApiResponse.ok(SimulationController.summary(sim));
    }

    @PostMapping("/start")
    public ApiResponse<Map<String, Object>> start(@RequestParam String simulationId) {
        return ApiResponse.ok(Map.of(
                "simulation_id", simulationId,
                "hint", "use POST /api/v1/simulations/{id}/start to run the scheduling loop"));
    }

    @PostMapping("/stop")
    public ApiResponse<Map<String, Object>> stop(@RequestParam String simulationId) {
        return ApiResponse.ok(SimulationController.summary(simulations.stop(simulationId)));
    }

    /** Latest decision plus the state vector that produced it - the debug view of Section 2. */
    @GetMapping("/decision")
    public ApiResponse<Map<String, Object>> latestDecision(@RequestParam String simulationId) {
        var live = simulations.liveState(simulationId);
        var frame = live.latestFrame();

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("simulation_id", simulationId);
        if (frame == null) {
            body.put("decision", null);
            return ApiResponse.ok(body);
        }
        Map<String, Object> decision = new LinkedHashMap<>();
        decision.put("t", frame.t());
        decision.put("action", Map.of("next_band", frame.action()));
        decision.put("model_id", frame.modelId());
        decision.put("reward", frame.reward());
        decision.put("reward_terms", frame.rewardTerms());
        decision.put("scanned_bands", frame.scannedBands());
        decision.put("detected_bands", frame.detectedBands());
        body.put("decision", decision);
        return ApiResponse.ok(body);
    }

    /** Paginated decision log. Backed by live state; persisted history arrives with Level 9. */
    @GetMapping("/history")
    public ApiResponse<Map<String, Object>> history(
            @RequestParam String simulationId,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "50") int size) {
        var live = simulations.liveState(simulationId);
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("simulation_id", simulationId);
        body.put("current_step", live.currentStep());
        body.put("latest", live.snapshot());
        body.put("page", page);
        body.put("size", size);
        return ApiResponse.ok(body);
    }

    /** The seven Section 13 scenarios, so the Frontend does not hardcode them. */
    @GetMapping("/scenarios")
    public ApiResponse<List<Map<String, Object>>> scenarios() {
        return ApiResponse.ok(ScenarioLibrary.all().stream().map(s -> {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("id", s.id());
            m.put("name", s.name());
            m.put("bands", s.bands());
            m.put("emitters", s.emitters());
            m.put("duration_steps", s.durationSteps());
            m.put("episodes", s.episodes());
            m.put("emitter_mix", s.emitterMix());
            m.put("expected_outcome", s.expectedOutcome());
            return m;
        }).toList());
    }
}

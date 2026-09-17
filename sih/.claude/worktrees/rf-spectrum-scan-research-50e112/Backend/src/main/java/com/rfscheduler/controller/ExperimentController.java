package com.rfscheduler.controller;

import com.rfscheduler.domain.ExperimentEntity;
import com.rfscheduler.dto.ApiResponse;
import com.rfscheduler.dto.Requests;
import com.rfscheduler.experiments.ExperimentService;
import com.rfscheduler.websocket.SimulationEventPublisher;
import jakarta.validation.Valid;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/** Experiments - the baseline-vs-ML comparison (API_CONTRACT.md Section 2, FR-009). */
@RestController
@RequestMapping("/api/v1/experiments")
public class ExperimentController {

    private final ExperimentService experiments;
    private final SimulationEventPublisher events;

    public ExperimentController(ExperimentService experiments, SimulationEventPublisher events) {
        this.experiments = experiments;
        this.events = events;
    }

    @PostMapping
    public ResponseEntity<ApiResponse<Map<String, Object>>> create(
            @Valid @RequestBody Requests.CreateExperiment body) {
        ExperimentEntity exp = experiments.create(body.name(), body.scenario(), body.policies(),
                body.episodes(), body.seed());
        return ResponseEntity.status(HttpStatus.CREATED).body(ApiResponse.ok(summary(exp)));
    }

    @GetMapping
    public ApiResponse<Map<String, Object>> list(
            @RequestParam(required = false) String status,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {
        Page<ExperimentEntity> found =
                experiments.list(status, PageRequest.of(Math.max(0, page), Math.min(size, 200)));
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("items", found.getContent().stream().map(ExperimentController::summary).toList());
        body.put("page", found.getNumber());
        body.put("size", found.getSize());
        body.put("total", found.getTotalElements());
        return ApiResponse.ok(body);
    }

    @GetMapping("/{id}")
    public ApiResponse<Map<String, Object>> get(@PathVariable String id) {
        ExperimentEntity exp = experiments.get(id);
        Map<String, Object> body = summary(exp);
        var progress = experiments.progress(id);
        if (progress != null) {
            body.put("progress", progress.asMap());
        }
        return ApiResponse.ok(body);
    }

    @PostMapping("/{id}/run")
    public ApiResponse<Map<String, Object>> run(
            @PathVariable String id,
            @RequestBody(required = false) Requests.RunExperiment body) {
        Integer duration = body == null ? null : body.durationSteps();
        ExperimentEntity exp = experiments.run(id, duration,
                (experimentId, progress) ->
                        events.publishExperimentProgress(experimentId, progress.asMap()));
        return ApiResponse.ok(summary(exp));
    }

    @PostMapping("/{id}/stop")
    public ApiResponse<Map<String, Object>> stop(@PathVariable String id) {
        return ApiResponse.ok(summary(experiments.stop(id)));
    }

    @GetMapping("/{id}/results")
    public ApiResponse<Map<String, Object>> results(@PathVariable String id) {
        return ApiResponse.ok(experiments.results(id));
    }

    static Map<String, Object> summary(ExperimentEntity exp) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("id", exp.getId());
        m.put("name", exp.getName());
        m.put("scenario", exp.getScenario());
        m.put("policies", exp.getPoliciesCsv().split(","));
        m.put("episodes", exp.getEpisodes());
        m.put("seed", exp.getSeed());
        m.put("status", exp.getStatus());
        m.put("expected_outcome", exp.getExpectedOutcome());
        m.put("created_at", exp.getCreatedAt());
        return m;
    }
}

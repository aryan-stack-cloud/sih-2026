package com.rfscheduler.controller;

import com.rfscheduler.dto.ApiResponse;
import com.rfscheduler.dto.Requests;
import com.rfscheduler.exception.ApiException;
import com.rfscheduler.ml.MlSchedulerClient;
import jakarta.validation.Valid;
import java.util.LinkedHashMap;
import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

/**
 * Model registry - a proxy onto Ai-ml-1 (Backend README Level 8).
 *
 * <p>The models themselves live in Ai-ml-1, which owns training and checkpoints. The Backend
 * exposes them under {@code /api/v1/models} so the Frontend has one host to talk to, per
 * API_CONTRACT.md Section 0. Nothing is cached here: a stale model list is worse than a slow one,
 * because activating the wrong model is invisible until the metrics look odd.
 */
@RestController
@RequestMapping("/api/v1/models")
public class ModelController {

    private final MlSchedulerClient scheduler;

    public ModelController(MlSchedulerClient scheduler) {
        this.scheduler = scheduler;
    }

    @PostMapping("/train")
    public ApiResponse<Map<String, Object>> train(@Valid @RequestBody Requests.TrainModel body) {
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("algorithm", body.algorithm());
        request.put("scenario", body.scenario().toUpperCase());
        request.put("hyperparams", body.hyperparams() == null ? Map.of() : body.hyperparams());
        if (body.episodeCount() != null) {
            request.put("episode_count", body.episodeCount());
        }
        return ApiResponse.ok(guard(() -> scheduler.train(request)));
    }

    @GetMapping("/train/{jobId}/status")
    public ApiResponse<Map<String, Object>> trainStatus(@PathVariable String jobId) {
        return ApiResponse.ok(guard(() -> scheduler.trainStatus(jobId)));
    }

    @GetMapping
    public ApiResponse<Object> list(
            @RequestParam(required = false) String algorithm,
            @RequestParam(required = false) Boolean active) {
        return ApiResponse.ok(guard(() -> scheduler.listModels(algorithm, active)));
    }

    @GetMapping("/{id}")
    public ApiResponse<Map<String, Object>> get(@PathVariable String id) {
        return ApiResponse.ok(guard(() -> scheduler.getModel(id)));
    }

    @PostMapping("/{id}/activate")
    public ApiResponse<Map<String, Object>> activate(@PathVariable String id) {
        return ApiResponse.ok(guard(() -> scheduler.activateModel(id)));
    }

    @PostMapping("/{id}/evaluate")
    public ApiResponse<Map<String, Object>> evaluate(
            @PathVariable String id, @Valid @RequestBody Requests.EvaluateModel body) {
        Map<String, Object> request = new LinkedHashMap<>();
        request.put("scenario", body.scenario().toUpperCase());
        request.put("episode_count", body.episodeCount() == null ? 20 : body.episodeCount());
        return ApiResponse.ok(guard(() -> scheduler.evaluateModel(id, request)));
    }

    /**
     * Turns an unreachable Ai-ml-1 into a 502 with a clear code, rather than a 500 that looks
     * like a Backend bug.
     */
    private static <T> T guard(java.util.function.Supplier<T> call) {
        try {
            return call.get();
        } catch (RuntimeException e) {
            throw ApiException.upstream("Ai-ml-1", String.valueOf(e.getMessage()));
        }
    }
}

package com.rfscheduler.dto;

import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.Pattern;
import java.util.List;

/**
 * Request bodies for the public API (API_CONTRACT.md Section 2).
 *
 * <p>Java records validated with jakarta.validation, so a constraint violation becomes a 422 with
 * a field-to-message map via {@code GlobalExceptionHandler} - exactly the shape Section 1
 * specifies.
 */
public final class Requests {

    private Requests() {
    }

    /** POST /simulations */
    public record CreateSimulation(
            @NotBlank(message = "name is required") String name,
            @Min(value = 1, message = "bands must be at least 1")
            @Max(value = 256, message = "bands must be at most 256") int bands,
            @Min(value = 1, message = "duration_steps must be at least 1")
            @Max(value = 100000, message = "duration_steps must be at most 100000") int durationSteps,
            Long seed,
            @Pattern(regexp = "^[A-Ga-g]$", message = "scenario must be one of A-G")
            String scenario,
            @Pattern(regexp = "^(baseline|random|bandit|q_learning|dqn|ppo|index|ctmc)$",
                    message = "policy must be one of baseline|random|bandit|q_learning|dqn|ppo|index|ctmc")
            String policy) {
    }

    /** PUT /simulations/{id} - every field optional; only draft simulations may be updated. */
    public record UpdateSimulation(
            String name,
            @Min(1) @Max(256) Integer bands,
            @Min(1) @Max(100000) Integer durationSteps,
            Long seed,
            @Pattern(regexp = "^(baseline|random|bandit|q_learning|dqn|ppo|index|ctmc)$")
            String policy) {
    }

    /** PUT /receiver/config */
    public record ReceiverConfigRequest(
            @Min(1) @Max(64) Integer bandwidthK,
            @Min(0) Integer dwellMs,
            @Min(0) Integer tuningDelayMs,
            @Min(1) Integer stepMs,
            Double threshold,
            Double snrMean,
            Double noiseSigma) {
    }

    /** PUT /scheduler/config */
    public record SchedulerConfigRequest(
            @NotBlank
            @Pattern(regexp = "^(baseline|random|bandit|q_learning|dqn|ppo|index|ctmc)$",
                    message = "policy must be one of baseline|random|bandit|q_learning|dqn|ppo|index|ctmc")
            String policy,
            String modelId) {
    }

    /** POST /experiments */
    public record CreateExperiment(
            String name,
            @NotBlank @Pattern(regexp = "^[A-Ga-g]$", message = "scenario must be one of A-G")
            String scenario,
            @NotEmpty(message = "at least one policy is required") List<String> policies,
            @Min(value = 1, message = "episodes must be at least 1") Integer episodes,
            Long seed) {
    }

    /** POST /experiments/{id}/run */
    public record RunExperiment(@Min(1) Integer durationSteps) {
    }

    /** POST /models/train - proxied to Ai-ml-1 /internal/train. */
    public record TrainModel(
            @NotBlank
            @Pattern(regexp = "^(bandit|q_learning|dqn|ppo)$",
                    message = "algorithm must be one of bandit|q_learning|dqn|ppo")
            String algorithm,
            @NotBlank @Pattern(regexp = "^[A-Ga-g]$") String scenario,
            java.util.Map<String, Object> hyperparams,
            @Min(1) Integer episodeCount) {
    }

    /** POST /models/{id}/evaluate */
    public record EvaluateModel(
            @NotBlank @Pattern(regexp = "^[A-Ga-g]$") String scenario,
            @Min(1) Integer episodeCount) {
    }

    /** POST /receiver/scan - manual single-step scan, for debugging. */
    public record ManualScan(@Min(0) int band) {
    }
}

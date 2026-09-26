package com.rfscheduler.experiments;

import tools.jackson.databind.json.JsonMapper;
import com.rfscheduler.domain.ExperimentEntity;
import com.rfscheduler.exception.ApiException;
import com.rfscheduler.metrics.MetricsSummary;
import com.rfscheduler.repository.ExperimentRepository;
import com.rfscheduler.service.SimulationRunner;
import com.rfscheduler.simulation.Scenario;
import com.rfscheduler.simulation.ScenarioLibrary;
import jakarta.annotation.PreDestroy;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.BiConsumer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.task.TaskExecutor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Runs the same scenario under several policies and compares them (FR-009, PRD Section 13).
 *
 * <p>THE CONTROL. Every policy is run on the <em>identical seed list</em>, so the spectrum is the
 * same for all of them and the only thing that differs is the scheduling decision. That is what
 * makes the headline baseline-vs-ML number an experiment rather than two unrelated runs, and it
 * is the single most important property of this class.
 *
 * <p>Section 13 asks for at least 20 episodes per policy for statistical stability. The default
 * comes from the scenario; a caller may lower it for a demo, and the response records what was
 * actually used so a comparison is never silently under-powered.
 */
@Service
public class ExperimentService {

    private static final Logger log = LoggerFactory.getLogger(ExperimentService.class);

    private final ExperimentRepository repository;
    private final SimulationRunner runner;
    private final TaskExecutor executor;
    // Spring Boot 4 ships Jackson 3, where databind lives under tools.jackson and the
    // concrete mapper is JsonMapper. Annotations stay on the com.fasterxml package.
    private final JsonMapper mapper = JsonMapper.builder().build();

    // A separate pool from `executor` on purpose. `execute()` below runs ON a thread borrowed
    // from `executor` and then blocks joining episode futures - scheduling those futures onto
    // that SAME bounded pool would starve it under load (every worker thread parked waiting on
    // children that can never get a worker thread to run on). Sized to cores because each episode
    // is CPU-bound simulation work plus blocking HTTP calls to Ai-ml-1, not I/O-bound waiting.
    private final ExecutorService episodeExecutor =
            Executors.newFixedThreadPool(Math.max(2, Runtime.getRuntime().availableProcessors()));

    /** Progress per running experiment, for WS training/experiment frames. */
    private final Map<String, Progress> progress = new ConcurrentHashMap<>();
    private final Map<String, String> activeInvocations = new ConcurrentHashMap<>();

    public ExperimentService(ExperimentRepository repository, SimulationRunner runner,
                             TaskExecutor simulationExecutor) {
        this.repository = repository;
        this.runner = runner;
        this.executor = simulationExecutor;
    }

    @PreDestroy
    void shutdownEpisodeExecutor() {
        episodeExecutor.shutdown();
        try {
            if (!episodeExecutor.awaitTermination(5, TimeUnit.SECONDS)) {
                episodeExecutor.shutdownNow();
            }
        } catch (InterruptedException e) {
            episodeExecutor.shutdownNow();
            Thread.currentThread().interrupt();
        }
    }

    @Transactional
    public ExperimentEntity create(String name, String scenarioId, List<String> policies,
                                   Integer episodes, Long seed) {
        Scenario scenario = ScenarioLibrary.byId(scenarioId);
        ExperimentEntity exp = new ExperimentEntity();
        exp.setId("exp_" + UUID.randomUUID().toString().replace("-", "").substring(0, 8));
        exp.setName(name == null || name.isBlank() ? scenario.name() : name);
        exp.setScenario(scenario.id());
        exp.setPoliciesCsv(String.join(",", policies));
        exp.setEpisodes(episodes == null ? scenario.episodes() : episodes);
        exp.setSeed(seed == null ? scenario.seed() : seed);
        exp.setStatus("draft");
        exp.setExpectedOutcome(scenario.expectedOutcome());
        exp.setCreatedAt(Instant.now());
        exp.setUpdatedAt(Instant.now());
        return repository.save(exp);
    }

    public Page<ExperimentEntity> list(String status, Pageable pageable) {
        return status == null || status.isBlank()
                ? repository.findAll(pageable)
                : repository.findByStatus(status, pageable);
    }

    public ExperimentEntity get(String id) {
        return repository.findById(id).orElseThrow(() -> ApiException.notFound("experiment", id));
    }

    /** Launches the comparison in the background. Progress is polled or streamed over WS. */
    public synchronized ExperimentEntity run(String id, Integer durationOverride,
                                BiConsumer<String, Progress> onProgress) {
        ExperimentEntity exp = get(id);
        if ("running".equals(exp.getStatus())) {
            throw ApiException.conflict("EXPERIMENT_ALREADY_RUNNING",
                    "experiment " + id + " is already running");
        }
        exp.setStatus("running");
        exp.setResultsJson(null);
        exp.setUpdatedAt(Instant.now());
        repository.save(exp);

        Scenario scenario = ScenarioLibrary.byId(exp.getScenario());
        List<String> policies = Arrays.stream(exp.getPoliciesCsv().split(","))
                .map(String::trim).filter(s -> !s.isEmpty()).toList();
        int episodes = exp.getEpisodes();
        long baseSeed = exp.getSeed();
        int duration = durationOverride == null ? scenario.durationSteps() : durationOverride;

        Progress state = new Progress(policies.size() * episodes);
        String invocationId = UUID.randomUUID().toString();
        activeInvocations.put(id, invocationId);
        progress.put(id, state);

        executor.execute(() -> {
            try {
                Map<String, Object> results = execute(
                        id, invocationId, scenario, policies, episodes, baseSeed, duration,
                        state, onProgress);
                if (!state.cancelled()) {
                    persistResults(id, invocationId, "completed", results);
                }
            } catch (RuntimeException e) {
                log.error("experiment {} failed", id, e);
                persistResults(id, invocationId, "failed",
                        Map.of("error", String.valueOf(e.getMessage())));
            } finally {
                state.finish();
                activeInvocations.remove(id, invocationId);
            }
        });
        return exp;
    }

    private Map<String, Object> execute(String experimentId, String invocationId,
                                        Scenario scenario,
                                        List<String> policies, int episodes, long baseSeed,
                                        int duration, Progress state,
                                        BiConsumer<String, Progress> onProgress) {

        // The shared seed list - the whole point of the class. Built once, used by every policy.
        List<Long> seeds = new ArrayList<>(episodes);
        for (int i = 0; i < episodes; i++) {
            seeds.add(baseSeed + i);
        }

        Map<String, Object> byPolicy = new LinkedHashMap<>();
        for (String policy : policies) {
            if (state.cancelled()) {
                break;
            }
            // Episodes within a policy are independent by construction (NFR-006: separate seed
            // streams, no shared mutable state) - the whole point of the shared seed list above is
            // that each one is a self-contained rerun of the same spectrum. Running them
            // concurrently is a straight wall-clock win, not just a "one thread does more" trick:
            // the ML-backed episodes each block on hundreds of /internal/decide round trips, so
            // three of them one at a time is three round-trip queues back to back for no reason.
            AtomicInteger completed = new AtomicInteger(0);
            List<CompletableFuture<SimulationRunner.RunResult>> futures = new ArrayList<>(episodes);
            for (int i = 0; i < episodes; i++) {
                long seed = seeds.get(i);
                var request = new SimulationRunner.RunRequest(
                        experimentId + "_" + invocationId + "_" + policy + "_" + i,
                        scenario, policy, seed, duration,
                        null, null);
                futures.add(CompletableFuture.supplyAsync(() -> {
                    SimulationRunner.RunResult result = runner.run(request, null, new SimulationRunner.LiveControl() {
                        @Override
                        public boolean stopRequested() {
                            return state.cancelled();
                        }

                        @Override
                        public long stepDelayMs() {
                            return 0;
                        }
                    });
                    if (state.cancelled()) {
                        return result;
                    }
                    // Episodes finish out of order under concurrency; the count of how many of
                    // this policy's episodes are done is still meaningful, the index isn't.
                    publishProgressIfCurrent(experimentId, invocationId, state, policy,
                            completed.incrementAndGet(), episodes, onProgress);
                    return result;
                }, episodeExecutor));
            }
            List<SimulationRunner.RunResult> runs = futures.stream()
                    .map(CompletableFuture::join).toList();
            Map<String, Object> policyResult = new LinkedHashMap<>(MetricsSummary.aggregate(
                    runs.stream().map(SimulationRunner.RunResult::metrics).toList()));
            policyResult.put("ml_decisions", runs.stream()
                    .mapToInt(SimulationRunner.RunResult::mlDecisions).sum());
            policyResult.put("fallback_decisions", runs.stream()
                    .mapToInt(SimulationRunner.RunResult::fallbackDecisions).sum());
            policyResult.put("degraded_episodes", (int) runs.stream()
                    .filter(SimulationRunner.RunResult::degraded).count());
            Set<String> modelIds = new TreeSet<>();
            runs.forEach(run -> modelIds.addAll(run.servedModelIds()));
            policyResult.put("model_ids", List.copyOf(modelIds));
            runs.stream().map(SimulationRunner.RunResult::unavailableReason)
                    .filter(reason -> reason != null && !reason.isBlank()).findFirst()
                    .ifPresent(reason -> policyResult.put("unavailable_reason", reason));
            byPolicy.put(policy, policyResult);
        }

        Map<String, Object> results = new LinkedHashMap<>();
        results.put("scenario", scenario.id());
        results.put("scenario_name", scenario.name());
        results.put("episodes", episodes);
        results.put("duration_steps", duration);
        results.put("seeds", seeds);
        results.put("expected_outcome", scenario.expectedOutcome());
        results.put("policies", byPolicy);
        results.put("comparison", compare(byPolicy));
        return results;
    }

    /**
     * Deltas of each learned policy against the open-loop reference.
     *
     * <p>Reports censored AIT as well as raw AIT. Raw AIT only averages the activation runs a
     * policy actually caught, so a policy that intercepts more runs looks worse on it - see
     * {@code MetricsEngine}. A comparison table that showed only raw AIT would mislead.
     */
    Map<String, Object> compare(Map<String, Object> byPolicy) {
        Object referenceKey = byPolicy.containsKey("baseline") ? "baseline"
                : byPolicy.containsKey("random") ? "random" : null;
        if (referenceKey == null) {
            return Map.of();
        }

        @SuppressWarnings("unchecked")
        Map<String, Object> reference = (Map<String, Object>) byPolicy.get(referenceKey);
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("reference", referenceKey);

        List<String> metrics = List.of("pd", "pfa", "ait", "ait_censored", "hpdr",
                "interception_ratio", "scan_efficiency", "run_intercept_rate");

        for (Map.Entry<String, Object> entry : byPolicy.entrySet()) {
            if (entry.getKey().equals(referenceKey)) {
                continue;
            }
            @SuppressWarnings("unchecked")
            Map<String, Object> policy = (Map<String, Object>) entry.getValue();
            if (toDouble(policy.get("ml_decisions")) == 0
                    && toDouble(policy.get("fallback_decisions")) > 0) {
                Object reason = policy.get("unavailable_reason");
                out.put(entry.getKey(), Map.of("status", "fell_back_to_sweep",
                        "reason", reason instanceof String s ? s
                                : "No ML decisions were served; the run used the fallback sweep"));
                continue;
            }
            Map<String, Object> deltas = new LinkedHashMap<>();
            for (String metric : metrics) {
                double base = toDouble(reference.get(metric));
                double value = toDouble(policy.get(metric));
                Map<String, Object> delta = new LinkedHashMap<>();
                delta.put("value", value);
                delta.put("reference", base);
                delta.put("absolute", value - base);
                delta.put("percent", base == 0 ? null : 100.0 * (value / base - 1.0));
                deltas.put(metric, delta);
            }
            out.put(entry.getKey(), deltas);
        }
        return out;
    }

    private static double toDouble(Object v) {
        return v instanceof Number n ? n.doubleValue() : 0.0;
    }

    private synchronized void publishProgressIfCurrent(String id, String invocationId,
                                                       Progress state, String policy, int episode,
                                                       int episodes,
                                                       BiConsumer<String, Progress> onProgress) {
        if (!invocationId.equals(activeInvocations.get(id)) || progress.get(id) != state) {
            return;
        }
        state.advance(policy, episode, episodes);
        if (onProgress != null) {
            onProgress.accept(id, state);
        }
    }

    @Transactional
    protected synchronized void persistResults(String id, String invocationId, String status,
                                               Map<String, Object> results) {
        if (!invocationId.equals(activeInvocations.get(id))) {
            return;
        }
        repository.findById(id).ifPresent(exp -> {
            // A cancellation is terminal for this invocation. Workers may finish their current
            // step after stop() returns, but they must not turn the visible status back into a
            // completed or failed run.
            if ("cancelled".equals(exp.getStatus())) {
                return;
            }
            exp.setStatus(status);
            exp.setUpdatedAt(Instant.now());
            try {
                exp.setResultsJson(mapper.writeValueAsString(results));
            } catch (Exception e) {
                exp.setResultsJson("{\"error\":\"failed to serialise results\"}");
            }
            repository.save(exp);
        });
    }

    public synchronized ExperimentEntity stop(String id) {
        ExperimentEntity exp = get(id);
        Progress state = progress.get(id);
        if (state != null) {
            state.cancel();
        }
        activeInvocations.remove(id);
        exp.setStatus("cancelled");
        exp.setUpdatedAt(Instant.now());
        return repository.save(exp);
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> results(String id) {
        ExperimentEntity exp = get(id);
        if (exp.getResultsJson() == null) {
            throw ApiException.conflict("EXPERIMENT_NOT_COMPLETE",
                    "experiment " + id + " is " + exp.getStatus() + "; no results yet");
        }
        try {
            return mapper.readValue(exp.getResultsJson(), Map.class);
        } catch (Exception e) {
            throw new ApiException(org.springframework.http.HttpStatus.INTERNAL_SERVER_ERROR,
                    "RESULTS_UNREADABLE", "stored results could not be parsed", Map.of());
        }
    }

    public Progress progress(String id) {
        return progress.get(id);
    }

    /** Coarse progress for an experiment run. */
    public static class Progress {

        private final int totalRuns;
        private volatile int completedRuns;
        private volatile String currentPolicy = "";
        private volatile int currentEpisode;
        private volatile int episodesPerPolicy;
        private volatile boolean cancelled;
        private volatile boolean finished;

        Progress(int totalRuns) {
            this.totalRuns = Math.max(1, totalRuns);
        }

        // Synchronized: episodes of one policy now complete concurrently (see execute() above),
        // so several threads can call this at once. `completedRuns++` alone is a lost-update race
        // under that; the read-modify-write needs to be atomic, not just each field volatile.
        synchronized void advance(String policy, int episode, int episodesPerPolicy) {
            this.currentPolicy = policy;
            this.currentEpisode = episode;
            this.episodesPerPolicy = episodesPerPolicy;
            this.completedRuns++;
        }

        void cancel() {
            this.cancelled = true;
        }

        void finish() {
            this.finished = true;
        }

        public boolean cancelled() {
            return cancelled;
        }

        public Map<String, Object> asMap() {
            Map<String, Object> m = new LinkedHashMap<>();
            m.put("fraction", Math.min(1.0, (double) completedRuns / totalRuns));
            m.put("completed_runs", completedRuns);
            m.put("total_runs", totalRuns);
            m.put("current_policy", currentPolicy);
            m.put("current_episode", currentEpisode);
            m.put("episodes_per_policy", episodesPerPolicy);
            m.put("finished", finished);
            m.put("cancelled", cancelled);
            return m;
        }
    }
}

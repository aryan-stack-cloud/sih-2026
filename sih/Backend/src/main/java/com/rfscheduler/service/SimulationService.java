package com.rfscheduler.service;

import com.rfscheduler.config.SimulationProperties;
import com.rfscheduler.domain.SimulationEntity;
import com.rfscheduler.exception.ApiException;
import com.rfscheduler.metrics.MetricsSummary;
import com.rfscheduler.ml.MlPeriodicityClient;
import com.rfscheduler.ml.MlSchedulerClient;
import com.rfscheduler.repository.SimulationRepository;
import com.rfscheduler.simulation.Scenario;
import com.rfscheduler.simulation.ScenarioLibrary;
import java.time.Instant;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.task.TaskExecutor;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Lifecycle and persistence for simulations - API_CONTRACT.md Section 2.
 *
 * <p>The entity is the system of record; the running simulation is a background job on the worker
 * pool. Live per-step state stays in memory (see {@link LiveSimulation}) and only progress and
 * final metrics are written back, because persisting every step of a 3000-step run inside the
 * request path would dominate the per-step latency budget.
 *
 * <p>Concurrency is capped at {@code rfscheduler.simulation.max-concurrent} (NFR-004, at least 5).
 * Exceeding it is a 409 rather than a queue, so a caller learns immediately instead of waiting.
 */
@Service
public class SimulationService {

    private static final Logger log = LoggerFactory.getLogger(SimulationService.class);

    private final SimulationRepository repository;
    private final SimulationRunner runner;
    private final MlSchedulerClient schedulerClient;
    private final MlPeriodicityClient periodicityClient;
    private final TaskExecutor executor;
    private final SimulationProperties props;

    /** Live state for running simulations, keyed by simulation id. */
    private final Map<String, LiveSimulation> live = new ConcurrentHashMap<>();
    private final AtomicInteger running = new AtomicInteger();

    public SimulationService(SimulationRepository repository,
                             SimulationRunner runner,
                             MlSchedulerClient schedulerClient,
                             MlPeriodicityClient periodicityClient,
                             TaskExecutor simulationExecutor,
                             SimulationProperties props) {
        this.repository = repository;
        this.runner = runner;
        this.schedulerClient = schedulerClient;
        this.periodicityClient = periodicityClient;
        this.executor = simulationExecutor;
        this.props = props;
    }

    // -- CRUD ---------------------------------------------------------------------------------

    @Transactional
    public SimulationEntity create(String name, int bands, int durationSteps, Long seed,
                                   String scenarioId, String policyType) {
        SimulationEntity sim = new SimulationEntity();
        sim.setId("sim_" + UUID.randomUUID().toString().replace("-", "").substring(0, 8));
        sim.setName(name);
        sim.setBands(bands);
        sim.setDurationSteps(durationSteps);
        sim.setSeed(seed == null ? 42L : seed);
        sim.setScenarioId(scenarioId);
        sim.setPolicyType(policyType == null ? "baseline" : policyType);
        sim.setStatus("draft");
        sim.setCurrentStep(0);
        sim.setCreatedAt(Instant.now());
        sim.setUpdatedAt(Instant.now());
        return repository.save(sim);
    }

    public Page<SimulationEntity> list(String status, Pageable pageable) {
        return status == null || status.isBlank()
                ? repository.findAll(pageable)
                : repository.findByStatus(status, pageable);
    }

    public SimulationEntity get(String id) {
        return repository.findById(id).orElseThrow(() -> ApiException.notFound("simulation", id));
    }

    @Transactional
    public SimulationEntity update(String id, String name, Integer bands, Integer durationSteps,
                                   Long seed, String policyType) {
        SimulationEntity sim = get(id);
        if (!"draft".equals(sim.getStatus())) {
            // Contract: "Update config (only while status=draft)".
            throw ApiException.conflict("SIMULATION_NOT_DRAFT",
                    "simulation " + id + " is " + sim.getStatus() + "; only draft may be updated");
        }
        if (name != null) {
            sim.setName(name);
        }
        if (bands != null) {
            sim.setBands(bands);
        }
        if (durationSteps != null) {
            sim.setDurationSteps(durationSteps);
        }
        if (seed != null) {
            sim.setSeed(seed);
        }
        if (policyType != null) {
            sim.setPolicyType(policyType);
        }
        sim.setUpdatedAt(Instant.now());
        return repository.save(sim);
    }

    @Transactional
    public void delete(String id) {
        SimulationEntity sim = get(id);
        live.remove(id);
        repository.delete(sim);   // scan/detection events cascade via the FK
    }

    // -- lifecycle ------------------------------------------------------------------------------

    /** Enqueues the simulation worker job. Returns immediately; progress arrives over WebSocket. */
    @Transactional
    public SimulationEntity start(String id, StepListener listener) {
        SimulationEntity sim = get(id);
        if ("running".equals(sim.getStatus())) {
            throw ApiException.conflict("SIMULATION_ALREADY_RUNNING",
                    "simulation " + id + " is already running");
        }
        if (running.get() >= props.maxConcurrent()) {
            throw ApiException.conflict("TOO_MANY_SIMULATIONS",
                    "at most " + props.maxConcurrent() + " simulations may run concurrently");
        }

        sim.setStatus("running");
        sim.setCurrentStep(0);
        sim.setUpdatedAt(Instant.now());
        repository.save(sim);

        LiveSimulation state = new LiveSimulation(id);
        live.put(id, state);
        running.incrementAndGet();

        Scenario scenario = resolveScenario(sim);
        var request = new SimulationRunner.RunRequest(
                id, scenario, sim.getPolicyType(), sim.getSeed(), sim.getDurationSteps(),
                null, null);

        executor.execute(() -> {
            try {
                var result = runner.run(request, frame -> {
                    state.record(frame);
                    if (listener != null) {
                        listener.onStep(id, frame);
                    }
                });
                state.complete(result.metrics());
                finish(id, "completed", result.steps());
                if (listener != null) {
                    listener.onComplete(id, result);
                }
            } catch (RuntimeException e) {
                log.error("simulation {} failed", id, e);
                state.fail(e.getMessage());
                finish(id, "failed", state.currentStep());
                if (listener != null) {
                    listener.onError(id, e.getMessage());
                }
            } finally {
                running.decrementAndGet();
            }
        });
        return sim;
    }

    @Transactional
    public SimulationEntity stop(String id) {
        SimulationEntity sim = get(id);
        LiveSimulation state = live.get(id);
        if (state != null) {
            state.requestStop();
        }
        sim.setStatus("stopped");
        sim.setCurrentStep(state == null ? sim.getCurrentStep() : state.currentStep());
        sim.setUpdatedAt(Instant.now());
        return repository.save(sim);
    }

    /**
     * Resets to t=0 and clears history.
     *
     * <p>Both ML services are reset too. Skipping either one means the next run of this
     * simulation id inherits the previous run's learned beliefs - Ai-ml-1's online bandit
     * estimates, or Ai-ml-2's detection buffers (API_CONTRACT.md Sections 4 and 5).
     */
    @Transactional
    public SimulationEntity reset(String id) {
        SimulationEntity sim = get(id);
        live.remove(id);
        schedulerClient.reset(id);
        periodicityClient.reset(id);
        sim.setStatus("draft");
        sim.setCurrentStep(0);
        sim.setUpdatedAt(Instant.now());
        return repository.save(sim);
    }

    @Transactional
    protected void finish(String id, String status, int steps) {
        repository.findById(id).ifPresent(sim -> {
            sim.setStatus(status);
            sim.setCurrentStep(steps);
            sim.setUpdatedAt(Instant.now());
            repository.save(sim);
        });
    }

    // -- live views ------------------------------------------------------------------------------

    public LiveSimulation liveState(String id) {
        LiveSimulation state = live.get(id);
        if (state == null) {
            throw ApiException.conflict("SIM_NOT_RUNNING",
                    "simulation " + id + " has no live state; start it first");
        }
        return state;
    }

    public LiveSimulation liveStateOrNull(String id) {
        return live.get(id);
    }

    public int runningCount() {
        return running.get();
    }

    private Scenario resolveScenario(SimulationEntity sim) {
        if (sim.getScenarioId() != null && !sim.getScenarioId().isBlank()) {
            Scenario base = ScenarioLibrary.byId(sim.getScenarioId());
            // The stored bands/duration win, so a caller can shorten a scenario for a demo.
            return new Scenario(base.id(), base.name(), sim.getBands(), base.emitters(),
                    sim.getDurationSteps(), base.episodes(), sim.getSeed(), base.emitterMix(),
                    base.highPriorityFraction(), base.receiver(), base.emitterParams(),
                    base.expectedOutcome());
        }
        Scenario base = ScenarioLibrary.byId("D");
        return new Scenario("custom", sim.getName(), sim.getBands(),
                Math.max(1, sim.getBands() / 2), sim.getDurationSteps(), 1, sim.getSeed(),
                base.emitterMix(), base.highPriorityFraction(), base.receiver(),
                base.emitterParams(), "Custom simulation");
    }

    /** Callback for streaming progress out to the WebSocket hub. */
    public interface StepListener {
        void onStep(String simulationId, SimulationRunner.StepFrame frame);

        default void onComplete(String simulationId, SimulationRunner.RunResult result) {
        }

        default void onError(String simulationId, String message) {
        }
    }

    /** In-memory state of one running simulation, for the live views and WS replay. */
    public static class LiveSimulation {

        private final String simulationId;
        private volatile SimulationRunner.StepFrame latest;
        private volatile MetricsSummary metrics;
        private volatile String error;
        private volatile boolean stopRequested;
        private final AtomicInteger step = new AtomicInteger();
        private final Map<String, Object> counters = new ConcurrentHashMap<>();

        LiveSimulation(String simulationId) {
            this.simulationId = simulationId;
            counters.put("detections", 0);
            counters.put("false_alarms", 0);
            counters.put("reward", 0.0);
        }

        void record(SimulationRunner.StepFrame frame) {
            latest = frame;
            step.set(frame.t());
            counters.merge("detections", frame.detectedBands().size(),
                    (a, b) -> ((Number) a).intValue() + ((Number) b).intValue());
            counters.merge("false_alarms", frame.falseAlarmBands().size(),
                    (a, b) -> ((Number) a).intValue() + ((Number) b).intValue());
            counters.merge("reward", frame.reward(),
                    (a, b) -> ((Number) a).doubleValue() + ((Number) b).doubleValue());
        }

        void complete(MetricsSummary summary) {
            this.metrics = summary;
        }

        void fail(String message) {
            this.error = message;
        }

        void requestStop() {
            this.stopRequested = true;
        }

        public boolean stopRequested() {
            return stopRequested;
        }

        public int currentStep() {
            return step.get();
        }

        public SimulationRunner.StepFrame latestFrame() {
            return latest;
        }

        public MetricsSummary metrics() {
            return metrics;
        }

        public String error() {
            return error;
        }

        /** Snapshot used by GET /metrics/live and by the WebSocket reconnect replay. */
        public Map<String, Object> snapshot() {
            Map<String, Object> out = new LinkedHashMap<>();
            out.put("simulation_id", simulationId);
            out.put("t", step.get());
            out.put("counters", new HashMap<>(counters));
            if (latest != null) {
                out.put("last_action", latest.action());
                out.put("scanned_bands", latest.scannedBands());
                out.put("active_bands", latest.activeBands());
                out.put("detected_bands", latest.detectedBands());
                out.put("reward", latest.reward());
                out.put("model_id", latest.modelId());
            }
            if (metrics != null) {
                out.put("metrics", metrics.asMap());
            }
            if (error != null) {
                out.put("error", error);
            }
            return out;
        }
    }
}

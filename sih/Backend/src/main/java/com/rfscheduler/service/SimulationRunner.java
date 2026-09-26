package com.rfscheduler.service;

import com.rfscheduler.metrics.MetricsEngine;
import com.rfscheduler.metrics.MetricsSummary;
import com.rfscheduler.metrics.RewardContext;
import com.rfscheduler.metrics.RewardFunction;
import com.rfscheduler.metrics.RewardWeights;
import com.rfscheduler.ml.BandPeriodicity;
import com.rfscheduler.ml.MlPeriodicityClient;
import com.rfscheduler.ml.MlSchedulerClient;
import com.rfscheduler.ml.NoCompatibleModelException;
import com.rfscheduler.ml.ScanDecision;
import com.rfscheduler.ml.StateBuilder;
import com.rfscheduler.receiver.DetectionEngine;
import com.rfscheduler.receiver.DetectionOutcome;
import com.rfscheduler.receiver.Observation;
import com.rfscheduler.receiver.Receiver;
import com.rfscheduler.receiver.Scanner;
import com.rfscheduler.simulation.Emitter;
import com.rfscheduler.simulation.EmitterFactory;
import com.rfscheduler.simulation.GroundTruth;
import com.rfscheduler.simulation.Scenario;
import com.rfscheduler.simulation.Seeding;
import com.rfscheduler.simulation.Spectrum;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import java.util.function.Consumer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

/**
 * The simulation loop - PRD Section 8.2, and the orchestration seam of the whole system.
 *
 * <pre>
 *   spectrum.advance(t)
 *   periodicity  = Ai-ml-2 batch predict          (one round trip, all bands)
 *   state        = stateBuilder.toContract(...)   (simulation features + periodicity merged)
 *   action       = Ai-ml-1 /internal/decide       (or BaselineScheduler)
 *   observation  = scanner.execute(action)
 *   event        = detectionEngine.evaluate(observation)
 *   reward       = rewardFn(event, action, state) (Equation 10.1, computed HERE)
 *   Ai-ml-2 /internal/periodicity/update          (per confirmed detection)
 *   Ai-ml-1 /internal/learn                       (reward posted back)
 *   metrics.record(...)
 * </pre>
 *
 * <p>Three ordering facts that are easy to get wrong and matter:
 *
 * <ul>
 *   <li><b>Periodicity is fetched before the decision, not after.</b> Ai-ml-1 never calls Ai-ml-2;
 *       this class is what stitches their outputs together (API_CONTRACT.md Section 0).
 *   <li><b>The reward is computed here.</b> Ai-ml-1 consumes the scalar and never recomputes
 *       Equation 10.1. {@code RewardFunctionParityTest} pins the two implementations together.
 *   <li><b>Band ages are snapshotted before the state update.</b> C(t) asks how recently we last
 *       visited a band, which is a fact about the step we are scoring, not the one after it.
 * </ul>
 */
@Service
public class SimulationRunner {

    private static final Logger log = LoggerFactory.getLogger(SimulationRunner.class);

    private final MlSchedulerClient schedulerClient;
    private final MlPeriodicityClient periodicityClient;

    public SimulationRunner(MlSchedulerClient schedulerClient,
                            MlPeriodicityClient periodicityClient) {
        this.schedulerClient = schedulerClient;
        this.periodicityClient = periodicityClient;
    }

    /** One episode of one policy against one seed. */
    public RunResult run(RunRequest request) {
        return run(request, null, null);
    }

    /**
     * One episode, optionally streaming per-step frames to a listener (the WebSocket hub).
     *
     * @param onStep called after every step; must not block for long
     */
    public RunResult run(RunRequest request, Consumer<StepFrame> onStep) {
        return run(request, onStep, null);
    }

    /**
     * @param onStep  called after every step; must not block for long
     * @param control live playback control for an interactively-watched run (stop, pacing).
     *                Never passed for batch experiment episodes, which always run at full speed.
     */
    public RunResult run(RunRequest request, Consumer<StepFrame> onStep, LiveControl control) {
        Scenario scenario = request.scenario();
        int numBands = scenario.bands();
        int duration = request.durationSteps() > 0
                ? Math.min(request.durationSteps(), scenario.durationSteps())
                : scenario.durationSteps();
        long seed = request.seed();
        String policy = request.policy();
        boolean usesMl = !"baseline".equals(policy) && !"random".equals(policy);

        // Independent streams: the world cannot be perturbed by the policy (NFR-006, Section 13).
        Random groundTruthRng = Seeding.groundTruth(seed);
        Random noiseRng = Seeding.noise(seed);
        Random policyRng = Seeding.policy(seed);

        List<Emitter> emitters = EmitterFactory.build(
                scenario.emitters(), numBands, scenario.emitterMix(), groundTruthRng,
                scenario.highPriorityFraction(), scenario.emitterParams());
        GroundTruth truth = new Spectrum(numBands).generate(emitters, duration, groundTruthRng);

        Receiver receiver = new Receiver(scenario.receiver(), numBands);
        Scanner scanner = new Scanner(receiver, noiseRng);
        DetectionEngine detectionEngine = new DetectionEngine(scenario.receiver().threshold());
        StateBuilder stateBuilder = new StateBuilder(numBands);
        MetricsEngine metrics = new MetricsEngine(truth);
        RewardFunction rewardFn = new RewardFunction(
                request.rewardWeights() == null ? RewardWeights.defaults() : request.rewardWeights());

        com.rfscheduler.scheduler.BaselineScheduler fallback =
                "random".equals(policy)
                        ? com.rfscheduler.scheduler.BaselineScheduler.random(numBands, policyRng)
                        : com.rfscheduler.scheduler.BaselineScheduler.roundRobin(
                                numBands, scenario.receiver().bandwidthK());
        fallback.reset();

        // A fresh simulation must not inherit the previous run's learned beliefs.
        if (usesMl) {
            schedulerClient.reset(request.simulationId());
            periodicityClient.reset(request.simulationId());
        }

        List<StepFrame> frames = new ArrayList<>();
        int mlDecisions = 0;
        int fallbackDecisions = 0;
        String unavailableReason = null;
        Set<String> servedModelIds = new HashSet<>();
        boolean stoppedEarly = false;
        Map<String, Object> previousState = null;

        for (int t = 0; t < duration; t++) {
            if (control != null && control.stopRequested()) {
                stoppedEarly = true;
                break;
            }

            // Step 0 needs an initial prediction. Later steps reuse the prediction fetched
            // after the preceding scan, which also makes /learn's next_state current.
            if (t == 0 && usesMl && request.periodicityEnabled()) {
                List<BandPeriodicity> periodicity =
                        periodicityClient.predictAll(request.simulationId(), numBands, t);
                for (BandPeriodicity bp : periodicity) {
                    stateBuilder.setPeriodicity(bp.bandId(), bp.phase(), bp.confidence());
                }
            }
            Map<String, Object> state = stateBuilder.toContract(receiver);

            // 2. Decide.
            ScanDecision decision = null;
            if (usesMl && unavailableReason == null) {
                try {
                    decision = schedulerClient.decide(request.simulationId(), state, policy,
                            request.modelId(), scenario.id());
                } catch (NoCompatibleModelException e) {
                    unavailableReason = policy + " has no trained model for scenario "
                            + scenario.id() + " (" + numBands + " bands)";
                    log.warn("{}; this run uses the fallback sweep", unavailableReason);
                    if (control != null) {
                        control.onUnavailable(unavailableReason);
                    }
                }
            }
            if (decision == null) {
                decision = ScanDecision.local(fallback.decide(), policy);
                // Only an ML policy falling back to the local sweep is degradation. For the
                // baseline and random policies the local scheduler IS the policy, and counting
                // it here reported every baseline run as degraded.
                if (usesMl) {
                    fallbackDecisions++;
                }
            } else {
                mlDecisions++;
                if (decision.modelId() != null && !decision.modelId().isBlank()) {
                    servedModelIds.add(decision.modelId());
                }
            }

            // 3. Scan and classify. Ages are snapshotted BEFORE the state update - see class doc.
            int[] agesBefore = stateBuilder.timeSinceLastScanSnapshot();
            // Current checkpoints select a band only; their optional dwell_time is not executed.
            Observation observation = scanner.execute(t, decision.nextBand(), truth.occupancyAt(t));
            DetectionOutcome outcome = detectionEngine.evaluate(observation, truth);

            // 4. Reward - Equation 10.1, computed here and only here.
            boolean[] highPriorityActive = new boolean[numBands];
            for (int b = 0; b < numBands; b++) {
                highPriorityActive[b] = truth.isHighPriorityActive(t, b);
            }
            List<Integer> scanned = observation.valid() ? observation.tunedBands() : List.of();
            RewardContext context = new RewardContext(
                    agesBefore, highPriorityActive, scanned, Math.max(2, numBands), 3);
            RewardFunction.RewardResult reward = rewardFn.compute(outcome, context);

            // 5. Tell Ai-ml-2 about every scan outcome, hits and misses alike.
            //
            // Reported for EVERY policy, not just the ML ones. A detection is a fact about the
            // spectrum, not about who chose to look - and gating this on `usesMl` meant a
            // baseline run fed the estimator nothing, so a warm-up sweep could not prime it and
            // the ablation arm saw a different history from the arm it was meant to control.
            // Reported in the ablation arm too, so the two arms differ only in the state merge.
            //
            // Misses matter just as much as hits (API_CONTRACT.md Section 5, "detected: false"):
            // this is the fix for the gap RUNNING.md documents - without it Ai-ml-2 cannot tell
            // "this band is quiet" from "this band was never looked at", which is why periodicity
            // prediction did not previously translate into a measurable scheduling benefit.
            // 6. Advance state, then merge t+1 periodicity before posting /learn.
            stateBuilder.update(scanned, outcome.detectedBands());
            boolean needsNextPrediction = usesMl && request.periodicityEnabled()
                    && t + 1 < duration && (control == null || !control.stopRequested());
            List<BandPeriodicity> nextPeriodicity = periodicityClient.step(
                    request.simulationId(), scanned, outcome.detectedBands(), t,
                    numBands, t + 1, needsNextPrediction);
            if (needsNextPrediction) {
                for (BandPeriodicity bp : nextPeriodicity) {
                    stateBuilder.setPeriodicity(bp.bandId(), bp.phase(), bp.confidence());
                }
            }
            Map<String, Object> nextState = stateBuilder.toContract(receiver);
            if (usesMl && decision.fromMl()) {
                schedulerClient.learn(request.simulationId(), decision.decisionId(), state,
                        decision.nextBand(), decision.dwellTime(), reward.reward(), nextState,
                        scanned, outcome.detectedBands());
            }

            metrics.record(outcome, observation.valid(), observation.retuned(), reward.reward());

            StepFrame frame = new StepFrame(
                    t, decision.nextBand(), scanned, truth.activeBands(t),
                    outcome.detectedBands(), outcome.falseAlarmBands(),
                    reward.reward(), reward.terms(), decision.modelId(), observation.valid());
            // Batch experiments need aggregate results, not thousands of retained step frames.
            if (onStep != null || control == null) {
                frames.add(frame);
            }
            if (onStep != null) {
                onStep.accept(frame);
            }
            previousState = nextState;

            // Pacing, for a human actually watching this run rather than a batch experiment
            // racing to a result. Sleeping AFTER the frame is emitted, not before, so the delay
            // is "how long this step stays on screen" rather than added latency before it appears.
            if (control != null) {
                long delayMs = control.stepDelayMs();
                if (delayMs > 0) {
                    try {
                        Thread.sleep(delayMs);
                    } catch (InterruptedException e) {
                        Thread.currentThread().interrupt();
                        stoppedEarly = true;
                        break;
                    }
                }
            }
        }

        MetricsSummary summary = metrics.summary();
        if (usesMl && fallbackDecisions > 0 && unavailableReason == null) {
            log.warn("simulation {} used the local fallback for {} of {} decisions",
                    request.simulationId(), fallbackDecisions, duration);
        }
        return new RunResult(request.simulationId(), policy, seed, duration, summary, frames,
                truth, mlDecisions, fallbackDecisions, stoppedEarly, Set.copyOf(servedModelIds),
                unavailableReason);
    }

    /**
     * Live control for an interactively-watched run. {@code SimulationService.LiveSimulation}
     * implements this directly - both fields are the same mutable, polled-once-per-step state a
     * viewer's Stop button and speed selector already need to reach, just read from the inside of
     * the loop instead of from the outside.
     */
    public interface LiveControl {
        boolean stopRequested();

        /** 0 (or less) means no pacing - run the step loop as fast as it can, today's default. */
        long stepDelayMs();

        default void onUnavailable(String reason) {
        }
    }

    // -- value types ------------------------------------------------------------------------

    /**
     * @param policy one of baseline|random|bandit|q_learning|dqn|ppo|index|ctmc (API_CONTRACT.md Section 6)
     */
    public record RunRequest(
            String simulationId,
            Scenario scenario,
            String policy,
            long seed,
            int durationSteps,
            String modelId,
            RewardWeights rewardWeights,
            boolean periodicityEnabled) {

        /** Default: Ai-ml-2's features are merged into the state. */
        public RunRequest(String simulationId, Scenario scenario, String policy, long seed,
                          int durationSteps, String modelId, RewardWeights rewardWeights) {
            this(simulationId, scenario, policy, seed, durationSteps, modelId, rewardWeights, true);
        }

        /**
         * The same run with the two periodicity features pinned to zero.
         *
         * <p>This is the controlled half of PRD Definition-of-Done item 8: identical scenario,
         * identical seed, identical policy, and the only difference is whether Ai-ml-2's
         * contribution reaches the state vector.
         */
        public RunRequest withoutPeriodicity() {
            return new RunRequest(simulationId, scenario, policy, seed, durationSteps, modelId,
                    rewardWeights, false);
        }
    }

    /** One step, in the shape the WebSocket spectrum_update / scan_decision frames need. */
    public record StepFrame(
            int t,
            int action,
            List<Integer> scannedBands,
            List<Integer> activeBands,
            List<Integer> detectedBands,
            List<Integer> falseAlarmBands,
            double reward,
            Map<String, Double> rewardTerms,
            String modelId,
            boolean validObservation) {
    }

    public record RunResult(
            String simulationId,
            String policy,
            long seed,
            int steps,
            MetricsSummary metrics,
            List<StepFrame> frames,
            GroundTruth groundTruth,
            int mlDecisions,
            int fallbackDecisions,
            boolean stoppedEarly,
            Set<String> servedModelIds,
            String unavailableReason) {

        /** True only when an ML policy had to fall back to the local sweep mid-run. */
        public boolean degraded() {
            return fallbackDecisions > 0;
        }
    }
}

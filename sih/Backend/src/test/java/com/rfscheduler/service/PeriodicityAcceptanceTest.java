package com.rfscheduler.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assumptions.assumeThat;

import com.rfscheduler.config.AppConfig;
import com.rfscheduler.config.MlProperties;
import com.rfscheduler.metrics.MetricsSummary;
import com.rfscheduler.metrics.RewardWeights;
import com.rfscheduler.ml.MlPeriodicityClient;
import com.rfscheduler.ml.MlSchedulerClient;
import com.rfscheduler.simulation.ScenarioLibrary;
import java.util.ArrayList;
import java.util.List;
import java.util.stream.LongStream;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestTemplate;

/**
 * Ai-ml-2 Level 9 acceptance gate / PRD Definition-of-Done item 8.
 *
 * <p>"Periodic-emitter prediction measurably improves detection latency on Scenario B."
 *
 * <p>This is the one gate that cannot be met from inside Ai-ml-2, because it is a statement about
 * the whole three-service loop: it needs the Backend to run Scenario B with and without Ai-ml-2's
 * output reaching the state vector Ai-ml-1 decides from.
 *
 * <p>THE CONTROL. Both arms use the same scenario, seed and policy, and both report their
 * observations into Ai-ml-2. The assigned intervention is whether {@code periodicity_phase} and
 * {@code periodicity_confidence} are merged into the state vector or left at zero. Once actions
 * diverge, the two arms can observe different bands and their estimator buffers can diverge too;
 * that downstream change is part of the end-to-end intervention being measured.
 *
 * <p>MEASURED ON CENSORED AIT, NOT RAW AIT. Raw AIT averages only the activation runs a policy
 * actually caught, so a policy that intercepts <em>more</em> runs reports a <em>worse</em> raw
 * AIT - the extra runs it caught are the hard, late ones the weaker arm missed entirely. Judging
 * this gate on raw AIT would rank the better configuration lower. See {@code MetricsEngine}.
 *
 * <p>The paired per-seed difference had SD about 17 steps in a 25-seed run, so five seeds had
 * standard error about 8 steps. A pooled comparison alone can pass a zero-effect change about
 * half the time: the pre-fix consumer passed it on 25 seeds, but its one-sided 95% upper bound
 * was +1.9 steps. The fixed consumer's bound was -3.3 on the same loop. The paired bound must
 * therefore be below zero to establish a measurable benefit.
 */
class PeriodicityAcceptanceTest {

    private static final MlProperties PROPS =
            new MlProperties("http://localhost:8500", "http://localhost:8600", 2000, 20000, true);

    private static final long[] SEEDS = LongStream.rangeClosed(42, 66).toArray();
    private static final int STEPS = 700;
    private static final double T_ONE_SIDED_95_DF_24 = 1.711;

    private static SimulationRunner runner;
    private static boolean servicesUp;

    @BeforeAll
    static void setUp() {
        RestTemplate rest = new AppConfig().mlRestTemplate(PROPS);

        MlSchedulerClient scheduler = new MlSchedulerClient(rest, PROPS);
        MlPeriodicityClient periodicity = new MlPeriodicityClient(rest, PROPS);
        runner = new SimulationRunner(scheduler, periodicity);
        servicesUp = scheduler.healthy() && periodicity.healthy();
    }

    private static SimulationRunner.RunRequest scenarioB(long seed, boolean withPeriodicity) {
        var request = new SimulationRunner.RunRequest(
                "sim_dod8" + (withPeriodicity ? "w" : "n") + Long.toHexString(seed),
                ScenarioLibrary.byId("B"), "index", seed, STEPS, null, RewardWeights.defaults());
        return withPeriodicity ? request : request.withoutPeriodicity();
    }

    @Test
    @DisplayName("DoD item 8: periodicity features improve detection latency on Scenario B")
    void periodicityImprovesDetectionLatencyOnScenarioB() {
        assertThat(SEEDS)
                .as("the df=24 t constant must change if the seed count changes")
                .hasSize(25);
        assumeThat(servicesUp)
                .as("Ai-ml-1 on :8500 and Ai-ml-2 on :8600 must be running")
                .isTrue();

        List<MetricsSummary> with = new ArrayList<>();
        List<MetricsSummary> without = new ArrayList<>();
        for (long seed : SEEDS) {
            with.add(runner.run(scenarioB(seed, true)).metrics());
            without.add(runner.run(scenarioB(seed, false)).metrics());
        }

        double sumDifference = 0.0;
        int improvedSeeds = 0;
        for (int i = 0; i < SEEDS.length; i++) {
            double difference = with.get(i).aitCensored() - without.get(i).aitCensored();
            sumDifference += difference;
            if (difference < 0.0) {
                improvedSeeds++;
            }
        }
        double meanDifference = sumDifference / SEEDS.length;
        double sumSquaredDeviations = 0.0;
        for (int i = 0; i < SEEDS.length; i++) {
            double difference = with.get(i).aitCensored() - without.get(i).aitCensored();
            sumSquaredDeviations += Math.pow(difference - meanDifference, 2);
        }
        double sampleSd = Math.sqrt(sumSquaredDeviations / (SEEDS.length - 1));
        double standardError = sampleSd / Math.sqrt(SEEDS.length);
        double upperBound = meanDifference + T_ONE_SIDED_95_DF_24 * standardError;

        var pooledWith = MetricsSummary.aggregate(with);
        var pooledWithout = MetricsSummary.aggregate(without);

        double aitWith = (double) pooledWith.get("ait_censored");
        double aitWithout = (double) pooledWithout.get("ait_censored");
        double runsWith = (double) pooledWith.get("run_intercept_rate");
        double runsWithout = (double) pooledWithout.get("run_intercept_rate");

        System.out.printf(
                "%n  PRD Definition-of-Done item 8 - Scenario B, %d seeds x %d steps%n"
                        + "    censored AIT       with=%8.1f   without=%8.1f   (%+.1f)%n"
                        + "    run intercept rate with=%8.4f   without=%8.4f%n"
                        + "    Pd                 with=%8.4f   without=%8.4f%n"
                        + "    HPDR               with=%8.4f   without=%8.4f%n"
                        + "    paired difference  mean=%+8.2f   SE=%6.2f   upper95=%+8.2f%n"
                        + "    seeds improved     %d/%d%n",
                SEEDS.length, STEPS,
                aitWith, aitWithout, aitWithout - aitWith,
                runsWith, runsWithout,
                (double) pooledWith.get("pd"), (double) pooledWithout.get("pd"),
                (double) pooledWith.get("hpdr"), (double) pooledWithout.get("hpdr"),
                meanDifference, standardError, upperBound,
                improvedSeeds, SEEDS.length);

        assertThat(aitWith)
                .as("censored AIT with periodicity (%.1f) should beat without (%.1f)",
                        aitWith, aitWithout)
                .isLessThanOrEqualTo(aitWithout);
        assertThat(upperBound)
                .as("one-sided 95%% paired upper bound (mean %.2f + %.3f * SE %.2f) must be below zero",
                        meanDifference, T_ONE_SIDED_95_DF_24, standardError)
                .isLessThan(0.0);
    }

    @Test
    @DisplayName("the ablation arm really does zero the periodicity features")
    void ablationActuallySuppressesTheFeatures() {
        assumeThat(servicesUp).isTrue();

        // Guards the control itself: if the switch silently did nothing, the gate above would
        // compare two identical runs and pass for the wrong reason.
        var withResult = runner.run(scenarioB(42L, true));
        var withoutResult = runner.run(scenarioB(42L, false));

        var withActions = withResult.frames().stream()
                .map(SimulationRunner.StepFrame::action).toList();
        var withoutActions = withoutResult.frames().stream()
                .map(SimulationRunner.StepFrame::action).toList();

        assertThat(withActions)
                .as("suppressing the features must change what the scheduler does")
                .isNotEqualTo(withoutActions);
    }
}

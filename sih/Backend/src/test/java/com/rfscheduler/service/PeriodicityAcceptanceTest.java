package com.rfscheduler.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assumptions.assumeThat;

import com.rfscheduler.config.MlProperties;
import com.rfscheduler.metrics.MetricsSummary;
import com.rfscheduler.metrics.RewardWeights;
import com.rfscheduler.ml.MlPeriodicityClient;
import com.rfscheduler.ml.MlSchedulerClient;
import com.rfscheduler.simulation.ScenarioLibrary;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
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
 * <p>THE CONTROL. Both arms use the same scenario, the same seed, the same policy, and report the
 * same detections into Ai-ml-2 - so the estimator's buffers are identical in both. The only
 * difference is whether {@code periodicity_phase} and {@code periodicity_confidence} are merged
 * into the state vector or left at zero. Anything that moves is attributable to that.
 *
 * <p>MEASURED ON CENSORED AIT, NOT RAW AIT. Raw AIT averages only the activation runs a policy
 * actually caught, so a policy that intercepts <em>more</em> runs reports a <em>worse</em> raw
 * AIT - the extra runs it caught are the hard, late ones the weaker arm missed entirely. Judging
 * this gate on raw AIT would rank the better configuration lower. See {@code MetricsEngine}.
 */
class PeriodicityAcceptanceTest {

    private static final MlProperties PROPS =
            new MlProperties("http://localhost:8500", "http://localhost:8600", 2000, 20000, true);

    private static final long[] SEEDS = {42L, 43L, 44L, 45L, 46L};
    private static final int STEPS = 700;

    private static SimulationRunner runner;
    private static boolean servicesUp;

    @BeforeAll
    static void setUp() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofMillis(PROPS.connectTimeoutMs()));
        factory.setReadTimeout(Duration.ofMillis(PROPS.readTimeoutMs()));
        RestTemplate rest = new RestTemplate(factory);

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
        assumeThat(servicesUp)
                .as("Ai-ml-1 on :8500 and Ai-ml-2 on :8600 must be running")
                .isTrue();

        List<MetricsSummary> with = new ArrayList<>();
        List<MetricsSummary> without = new ArrayList<>();
        for (long seed : SEEDS) {
            with.add(runner.run(scenarioB(seed, true)).metrics());
            without.add(runner.run(scenarioB(seed, false)).metrics());
        }

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
                        + "    HPDR               with=%8.4f   without=%8.4f%n",
                SEEDS.length, STEPS,
                aitWith, aitWithout, aitWithout - aitWith,
                runsWith, runsWithout,
                (double) pooledWith.get("pd"), (double) pooledWithout.get("pd"),
                (double) pooledWith.get("hpdr"), (double) pooledWithout.get("hpdr"));

        assertThat(aitWith)
                .as("censored AIT with periodicity (%.1f) should beat without (%.1f)",
                        aitWith, aitWithout)
                .isLessThanOrEqualTo(aitWithout);
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

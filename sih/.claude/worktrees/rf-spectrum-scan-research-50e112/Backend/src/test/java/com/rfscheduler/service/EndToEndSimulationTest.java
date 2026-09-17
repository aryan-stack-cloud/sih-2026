package com.rfscheduler.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assumptions.assumeThat;

import com.rfscheduler.config.MlProperties;
import com.rfscheduler.metrics.RewardWeights;
import com.rfscheduler.ml.MlPeriodicityClient;
import com.rfscheduler.ml.MlSchedulerClient;
import com.rfscheduler.simulation.Scenario;
import com.rfscheduler.simulation.ScenarioLibrary;
import java.time.Duration;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestTemplate;

/**
 * Backend Level 8 Definition of Done: a full baseline-vs-ML run end to end, no mocks.
 *
 * <p>This exercises the real seam - Backend -&gt; Ai-ml-2 (periodicity) -&gt; Backend
 * (StateBuilder) -&gt; Ai-ml-1 (decide) -&gt; Backend (reward) -&gt; Ai-ml-1 (learn). It is the
 * test that would catch a contract drift between the three services, which unit tests on either
 * side cannot.
 *
 * <p>Skipped, not failed, when the ML services are not running: this suite must stay green for
 * someone who has only checked out the Backend. Start them with:
 *
 * <pre>
 *   uvicorn ml.api.main:app --port 8500          # in Ai-ml-1-Scheduler-Engine
 *   uvicorn periodicity.api.main:app --port 8600 # in Ai-ml-2-Periodicity-Estimator
 * </pre>
 */
class EndToEndSimulationTest {

    private static final MlProperties PROPS =
            new MlProperties("http://localhost:8500", "http://localhost:8600", 2000, 15000, true);

    private static MlSchedulerClient schedulerClient;
    private static MlPeriodicityClient periodicityClient;
    private static SimulationRunner runner;
    private static boolean servicesUp;

    @BeforeAll
    static void setUp() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofMillis(PROPS.connectTimeoutMs()));
        factory.setReadTimeout(Duration.ofMillis(PROPS.readTimeoutMs()));
        RestTemplate rest = new RestTemplate(factory);

        schedulerClient = new MlSchedulerClient(rest, PROPS);
        periodicityClient = new MlPeriodicityClient(rest, PROPS);
        runner = new SimulationRunner(schedulerClient, periodicityClient);
        servicesUp = schedulerClient.healthy() && periodicityClient.healthy();
    }

    private static SimulationRunner.RunRequest request(String policy, long seed, int steps) {
        Scenario scenario = ScenarioLibrary.byId("B");
        return new SimulationRunner.RunRequest(
                "sim_e2e" + Long.toHexString(seed), scenario, policy, seed, steps, null,
                RewardWeights.defaults());
    }

    // -- the parts that need no ML service --------------------------------------------------

    @Test
    @DisplayName("baseline runs a full episode and produces scoreable metrics")
    void baselineRuns() {
        var result = runner.run(request("baseline", 42, 400));

        assertThat(result.steps()).isEqualTo(400);
        assertThat(result.frames()).hasSize(400);
        assertThat(result.fallbackDecisions()).isZero();   // baseline never calls out

        var m = result.metrics();
        assertThat(m.pd()).isBetween(0.0, 1.0);
        assertThat(m.totalRuns()).isPositive();
        assertThat(m.totalScans()).isPositive();
        assertThat(m.coverage()).isPositive();
    }

    @Test
    @DisplayName("the same seed gives a bit-identical run (NFR-006)")
    void reproducible() {
        var first = runner.run(request("baseline", 7, 300));
        var second = runner.run(request("baseline", 7, 300));

        assertThat(second.metrics().asMap()).isEqualTo(first.metrics().asMap());
        assertThat(second.frames().stream().map(SimulationRunner.StepFrame::action).toList())
                .isEqualTo(first.frames().stream().map(SimulationRunner.StepFrame::action).toList());
    }

    @Test
    @DisplayName("every policy sees an identical spectrum at the same seed (Section 13)")
    void sameSeedSameWorld() {
        var baseline = runner.run(request("baseline", 99, 200));
        var random = runner.run(request("random", 99, 200));

        // The worlds must match even though the scan orders do not.
        for (int t = 0; t < 200; t++) {
            assertThat(random.frames().get(t).activeBands())
                    .as("active bands at t=%d", t)
                    .isEqualTo(baseline.frames().get(t).activeBands());
        }
        assertThat(random.groundTruth().totalActivationRuns())
                .isEqualTo(baseline.groundTruth().totalActivationRuns());
    }

    @Test
    @DisplayName("the scheduler never sees ground truth")
    void groundTruthNeverLeaks() {
        var result = runner.run(request("baseline", 3, 120));
        // Detected bands are always a subset of the bands actually scanned: nothing is "detected"
        // on a band the receiver was not pointed at.
        for (var frame : result.frames()) {
            assertThat(frame.scannedBands()).containsAll(frame.detectedBands());
        }
    }

    // -- the real three-service path ----------------------------------------------------------

    @Test
    @DisplayName("Level 8 DoD: full bandit run through Ai-ml-2 and Ai-ml-1, no mocks")
    void banditRunsThroughBothMlServices() {
        assumeThat(servicesUp)
                .as("Ai-ml-1 on :8500 and Ai-ml-2 on :8600 must be running")
                .isTrue();

        var result = runner.run(request("bandit", 42, 300));

        assertThat(result.steps()).isEqualTo(300);
        assertThat(result.mlDecisions())
                .as("every decision should have come from Ai-ml-1")
                .isEqualTo(300);
        assertThat(result.fallbackDecisions()).isZero();
        assertThat(result.frames().get(0).modelId()).isNotBlank();
        assertThat(result.metrics().pd()).isPositive();
    }

    @Test
    @DisplayName("the learned policy beats the open-loop sweep on detection")
    void banditBeatsBaseline() {
        assumeThat(servicesUp).isTrue();

        var baseline = runner.run(request("baseline", 42, 600));
        var bandit = runner.run(request("bandit", 42, 600));

        assertThat(bandit.metrics().pd())
                .as("Pd: bandit %.4f vs baseline %.4f",
                        bandit.metrics().pd(), baseline.metrics().pd())
                .isGreaterThan(baseline.metrics().pd());
        assertThat(bandit.metrics().scanEfficiency())
                .isGreaterThan(baseline.metrics().scanEfficiency());
    }

    @Test
    @DisplayName("an ML outage degrades to the sweep instead of failing the run")
    void degradesGracefully() {
        MlProperties broken = new MlProperties(
                "http://localhost:59999", "http://localhost:59998", 200, 200, true);
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofMillis(200));
        factory.setReadTimeout(Duration.ofMillis(200));
        RestTemplate rest = new RestTemplate(factory);

        var offline = new SimulationRunner(
                new MlSchedulerClient(rest, broken), new MlPeriodicityClient(rest, broken));
        var result = offline.run(request("bandit", 42, 40));

        assertThat(result.steps()).isEqualTo(40);
        assertThat(result.fallbackDecisions()).isEqualTo(40);
        assertThat(result.degraded()).isTrue();
        assertThat(result.metrics().totalScans()).isPositive();
    }
}

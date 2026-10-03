package com.rfscheduler.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.rfscheduler.config.MlProperties;
import com.rfscheduler.metrics.RewardWeights;
import com.rfscheduler.ml.MlPeriodicityClient;
import com.rfscheduler.ml.MlSchedulerClient;
import com.rfscheduler.simulation.Scenario;
import com.rfscheduler.simulation.ScenarioLibrary;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestTemplate;

/**
 * Behavioural pacing test: the delay is the spacing between EMITTED frames.
 *
 * <p>Regression guard for the race view: the publisher's frame gate drops frames
 * emitted closer together than its minimum spacing, so every gap between
 * consecutive onStep emissions must be at least the pacing delay (minus a small
 * timer-granularity tolerance). No upper bound is asserted - that would be flaky.
 *
 * <p>No Mockito, no network: the baseline policy never calls Ai-ml-1, and the
 * per-step Ai-ml-2 call degrades to "zero features" against unreachable
 * loopback ports (connection refused fails immediately, never near the timeout).
 */
class SimulationRunnerPacingTest {

    private static final int STEPS = 6;
    private static final long DELAY_MS = 40;
    /** Timer-granularity tolerance below the delay; never an upper bound. */
    private static final long MIN_GAP_MS = DELAY_MS - 2;

    private static SimulationRunner offlineRunner() {
        MlProperties props =
                new MlProperties("http://localhost:59999", "http://localhost:59998", 100, 100, true);
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofMillis(100));
        factory.setReadTimeout(Duration.ofMillis(100));
        RestTemplate rest = new RestTemplate(factory);
        return new SimulationRunner(new MlSchedulerClient(rest, props),
                new MlPeriodicityClient(rest, props));
    }

    private static SimulationRunner.RunRequest request() {
        Scenario scenario = ScenarioLibrary.byId("B");
        return new SimulationRunner.RunRequest(
                "sim_pacing", scenario, "baseline", 11L, STEPS, null,
                RewardWeights.defaults());
    }

    private static SimulationRunner.LiveControl control(long delayMs) {
        return new SimulationRunner.LiveControl() {
            @Override
            public boolean stopRequested() {
                return false;
            }

            @Override
            public long stepDelayMs() {
                return delayMs;
            }
        };
    }

    @Test
    void emissionsAreSpacedByTheDelay() {
        SimulationRunner runner = offlineRunner();
        // Warmup: absorb one-off cold-JVM costs (class loading, first refused
        // connection, logger init) so the measured first step is pure compute.
        runner.run(request(), frame -> { }, control(0));

        List<Long> emittedAt = new ArrayList<>();
        long startNanos = System.nanoTime();

        var result = runner.run(request(), frame -> emittedAt.add(System.nanoTime()),
                control(DELAY_MS));

        assertThat(result.frames()).hasSize(STEPS);
        assertThat(emittedAt).hasSize(STEPS);
        // The pacing wait is skipped before the first emission: the first frame must
        // arrive after one step of compute, not after a full delay. The bound is the
        // delay itself, far above the few ms a baseline step needs.
        assertThat(emittedAt.get(0) - startNanos).isLessThan(DELAY_MS * 1_000_000L);
        for (int i = 1; i < emittedAt.size(); i++) {
            long gapMs = (emittedAt.get(i) - emittedAt.get(i - 1)) / 1_000_000L;
            assertThat(gapMs).as("gap before emission %d", i).isGreaterThanOrEqualTo(MIN_GAP_MS);
        }
        long spanMs = (emittedAt.get(emittedAt.size() - 1) - emittedAt.get(0)) / 1_000_000L;
        assertThat(spanMs).isGreaterThanOrEqualTo((STEPS - 1) * MIN_GAP_MS);
    }

    @Test
    void zeroDelayIsNotPaced() {
        SimulationRunner runner = offlineRunner();
        List<Long> emittedAt = new ArrayList<>();
        long startNanos = System.nanoTime();

        var result = runner.run(request(), frame -> emittedAt.add(System.nanoTime()),
                control(0));

        assertThat(result.frames()).hasSize(STEPS);
        assertThat(emittedAt).hasSize(STEPS);
        long spanMs = (emittedAt.get(emittedAt.size() - 1) - emittedAt.get(0)) / 1_000_000L;
        assertThat(spanMs).as("unpaced span for %d steps", STEPS).isLessThan(1_000L);
        assertThat(System.nanoTime() - startNanos).isLessThan(1_000_000_000L);
    }
}

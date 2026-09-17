package com.rfscheduler.metrics;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.rfscheduler.receiver.DetectionOutcome;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

/**
 * Reward parity with Ai-ml-1 (PRD Phase 5 DoD, TEST-010).
 *
 * <p>WHY THIS FILE EXISTS. In production the Backend computes Equation 10.1 and posts the scalar
 * to Ai-ml-1's {@code /internal/learn}. Ai-ml-1 carries its own copy only so standalone training
 * has a reward when no Backend is running. If the two drift, the agent is trained against one
 * objective and scored by another - and nothing errors. The numbers just get quietly worse.
 *
 * <p>Every case below is ported verbatim from
 * {@code Ai-ml-1-Scheduler-Engine/tests/test_reward.py}, including the stated arithmetic. If a
 * case changes on either side, it must change on both.
 */
class RewardFunctionParityTest {

    private static final RewardWeights W = new RewardWeights(10.0, 2.0, 3.0, 5.0, 0.5, 4.0);
    private static final RewardFunction REWARD = new RewardFunction(W);
    private static final int BANDS = 8;
    private static final double EPS = 1e-9;

    // -- fixtures mirroring the Python helpers ---------------------------------------------------

    private static DetectionOutcome outcome(
            List<Integer> detected,
            double maxPriority,
            List<Integer> falseAlarms,
            List<Integer> unscannedMisses,
            Map<Integer, Integer> detectionLatency,
            Map<Integer, Integer> newRunLatencies) {
        return new DetectionOutcome(10, Map.of(), unscannedMisses, detected, falseAlarms,
                Set.of(), maxPriority, detectionLatency, newRunLatencies);
    }

    private static DetectionOutcome nothing() {
        return outcome(List.of(), 0.0, List.of(), List.of(), Map.of(), Map.of());
    }

    private static RewardContext context(List<Integer> scanned) {
        return context(scanned, filled(99), new boolean[BANDS], 20);
    }

    private static RewardContext context(
            List<Integer> scanned, int[] ages, boolean[] highPriority, int horizon) {
        return new RewardContext(ages, highPriority, scanned, horizon, 3);
    }

    private static int[] filled(int value) {
        int[] ages = new int[BANDS];
        Arrays.fill(ages, value);
        return ages;
    }

    // -- the cases -------------------------------------------------------------------------------

    @Test
    @DisplayName("nothing happens scores zero")
    void nothingHappensScoresZero() {
        var result = REWARD.compute(nothing(), context(List.of()));
        assertThat(result.reward()).isZero();
        assertThat(result.terms()).containsExactlyInAnyOrderEntriesOf(
                Map.of("D", 0.0, "P", 0.0, "L", 0.0, "F", 0.0, "C", 0.0, "M", 0.0));
    }

    @Test
    @DisplayName("plain detection of a priority-1 emitter: 10*1 + 2*1*1 = 12")
    void plainDetection() {
        var result = REWARD.compute(
                outcome(List.of(3), 1.0, List.of(), List.of(), Map.of(), Map.of()),
                context(List.of(3)));
        assertThat(result.terms().get("D")).isEqualTo(1.0);
        assertThat(result.terms().get("P")).isEqualTo(1.0);
        assertThat(result.reward()).isCloseTo(12.0, org.assertj.core.data.Offset.offset(EPS));
    }

    @Test
    @DisplayName("high-priority detection pays the multiplier: 10 + 2*2 = 14")
    void highPriorityDetection() {
        var result = REWARD.compute(
                outcome(List.of(3), 2.0, List.of(), List.of(), Map.of(), Map.of()),
                context(List.of(3)));
        assertThat(result.reward()).isCloseTo(14.0, org.assertj.core.data.Offset.offset(EPS));
    }

    @Test
    @DisplayName("first interception of a run pays the latency penalty: 10 + 2 - 3*0.5 = 10.5")
    void firstInterceptionPaysLatency() {
        var result = REWARD.compute(
                outcome(List.of(3), 1.0, List.of(), List.of(), Map.of(3, 10), Map.of(3, 10)),
                context(List.of(3)));
        assertThat(result.terms().get("L")).isCloseTo(0.5, org.assertj.core.data.Offset.offset(EPS));
        assertThat(result.reward()).isCloseTo(10.5, org.assertj.core.data.Offset.offset(EPS));
    }

    @Test
    @DisplayName("latency is not charged again on re-detecting the same run")
    void latencyNotChargedTwice() {
        // detectionLatency is populated (we did detect), but newRunLatencies is empty.
        var result = REWARD.compute(
                outcome(List.of(3), 1.0, List.of(), List.of(), Map.of(3, 400), Map.of()),
                context(List.of(3)));
        assertThat(result.terms().get("L")).isZero();
        assertThat(result.reward()).isCloseTo(12.0, org.assertj.core.data.Offset.offset(EPS));
    }

    @Test
    @DisplayName("latency saturates at the horizon: 10 + 2 - 3 = 9")
    void latencySaturates() {
        var result = REWARD.compute(
                outcome(List.of(3), 1.0, List.of(), List.of(), Map.of(), Map.of(3, 999)),
                context(List.of(3)));
        assertThat(result.terms().get("L")).isEqualTo(1.0);
        assertThat(result.reward()).isCloseTo(9.0, org.assertj.core.data.Offset.offset(EPS));
    }

    @Test
    @DisplayName("false alarm penalty: -5")
    void falseAlarmPenalty() {
        var result = REWARD.compute(
                outcome(List.of(), 0.0, List.of(5), List.of(), Map.of(), Map.of()),
                context(List.of(5)));
        assertThat(result.terms().get("F")).isEqualTo(1.0);
        assertThat(result.reward()).isCloseTo(-5.0, org.assertj.core.data.Offset.offset(EPS));
    }

    @Test
    @DisplayName("redundant-scan penalty is a fraction of scanned bands")
    void redundantIsAFraction() {
        int[] ages = filled(99);
        ages[2] = 1;
        ages[3] = 2;
        var result = REWARD.compute(nothing(),
                context(List.of(2, 3), ages, new boolean[BANDS], 20));
        assertThat(result.terms().get("C")).isCloseTo(1.0, org.assertj.core.data.Offset.offset(EPS));
        assertThat(result.reward()).isCloseTo(-0.5, org.assertj.core.data.Offset.offset(EPS));
    }

    @Test
    @DisplayName("a band that intercepted a new run is not redundant")
    void newRunIsNotRedundant() {
        int[] ages = filled(1);
        var result = REWARD.compute(
                outcome(List.of(2), 1.0, List.of(), List.of(), Map.of(2, 0), Map.of(2, 0)),
                context(List.of(2, 3), ages, new boolean[BANDS], 20));
        // Band 2 intercepted a new run, band 3 gave nothing -> C = 1/2
        assertThat(result.terms().get("C")).isCloseTo(0.5, org.assertj.core.data.Offset.offset(EPS));
    }

    @Test
    @DisplayName("re-detecting an already-intercepted run counts as redundant")
    void reDetectionIsRedundant() {
        int[] ages = filled(1);
        var result = REWARD.compute(
                outcome(List.of(2), 1.0, List.of(), List.of(), Map.of(2, 300), Map.of()),
                context(List.of(2), ages, new boolean[BANDS], 20));
        assertThat(result.terms().get("C")).isCloseTo(1.0, org.assertj.core.data.Offset.offset(EPS));
    }

    @Test
    @DisplayName("bands not recently visited are not redundant")
    void staleBandsAreNotRedundant() {
        var result = REWARD.compute(nothing(),
                context(List.of(2, 3), filled(50), new boolean[BANDS], 20));
        assertThat(result.terms().get("C")).isZero();
    }

    @Test
    @DisplayName("missed opportunity is a fraction of active high-priority bands")
    void missedIsAFraction() {
        boolean[] high = new boolean[BANDS];
        high[1] = true;
        high[4] = true;
        high[6] = true;
        var result = REWARD.compute(
                outcome(List.of(), 0.0, List.of(), List.of(1, 4), Map.of(), Map.of()),
                context(List.of(6), filled(99), high, 20));
        assertThat(result.terms().get("M"))
                .isCloseTo(2.0 / 3.0, org.assertj.core.data.Offset.offset(EPS));
    }

    @Test
    @DisplayName("missed opportunity is zero when no high-priority band is active")
    void missedIsZeroWithoutHighPriority() {
        var result = REWARD.compute(
                outcome(List.of(), 0.0, List.of(), List.of(0, 1, 2), Map.of(), Map.of()),
                context(List.of(5)));
        assertThat(result.terms().get("M")).isZero();
    }

    @Test
    @DisplayName("full equation combines every term: 10 + 4 - 0.75 - 5 - 0.25 - 2 = 6.0")
    void fullEquation() {
        boolean[] high = new boolean[BANDS];
        high[0] = true;
        high[7] = true;
        int[] ages = filled(99);
        ages[1] = 1;

        var result = REWARD.compute(
                outcome(List.of(0), 2.0, List.of(1), List.of(7), Map.of(0, 5), Map.of(0, 5)),
                context(List.of(0, 1), ages, high, 20));

        assertThat(result.terms().get("D")).isEqualTo(1.0);
        assertThat(result.terms().get("P")).isEqualTo(2.0);
        assertThat(result.terms().get("L")).isCloseTo(0.25, org.assertj.core.data.Offset.offset(EPS));
        assertThat(result.terms().get("F")).isEqualTo(1.0);
        assertThat(result.terms().get("C")).isCloseTo(0.5, org.assertj.core.data.Offset.offset(EPS));
        assertThat(result.terms().get("M")).isCloseTo(0.5, org.assertj.core.data.Offset.offset(EPS));
        assertThat(result.reward()).isCloseTo(6.0, org.assertj.core.data.Offset.offset(EPS));
    }

    @Test
    @DisplayName("negative weights are rejected")
    void negativeWeightsRejected() {
        assertThatThrownBy(() -> new RewardWeights(-1.0, 2.0, 3.0, 5.0, 0.5, 4.0))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("non-negative");
    }

    @Test
    @DisplayName("shipped defaults match Ai-ml-1's ml/environments/reward.py")
    void defaultsMatchTheMlService() {
        RewardWeights defaults = RewardWeights.defaults();
        assertThat(defaults.w1Detection()).isEqualTo(10.0);
        assertThat(defaults.w2Priority()).isEqualTo(2.0);
        assertThat(defaults.w3Latency()).isEqualTo(3.0);
        assertThat(defaults.w4FalseAlarm()).isEqualTo(5.0);
        assertThat(defaults.w5Redundant()).isEqualTo(3.0);
        assertThat(defaults.w6Missed()).isEqualTo(4.0);
    }
}

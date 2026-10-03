package com.rfscheduler.service;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class LiveSimulationPerBandTest {

    private static SimulationRunner.StepFrame frame(int t, List<Integer> scanned,
            List<Integer> active, List<Integer> detected) {
        return new SimulationRunner.StepFrame(t, 0, scanned, active, detected,
                List.of(), 0.0, Map.of(), null, true);
    }

    @SuppressWarnings("unchecked")
    private static List<Integer> perBandList(SimulationService.LiveSimulation live, String key) {
        Map<String, Object> perBand =
                (Map<String, Object>) live.snapshot().get("per_band");
        return (List<Integer>) perBand.get(key);
    }

    @Test
    void countsAccumulateAcrossFrames() {
        var live = new SimulationService.LiveSimulation("sim_test", 4);
        live.record(frame(0, List.of(0, 1), List.of(1, 2), List.of(1)));
        live.record(frame(1, List.of(1), List.of(1), List.of(0, 1)));

        // looks: band 0 seen once, band 1 seen twice; active: band 1 twice, band 2 once;
        // heard: band 0 once, band 1 twice - the attention-vs-activity split the judge view needs.
        assertThat(perBandList(live, "looks")).containsExactly(1, 2, 0, 0);
        assertThat(perBandList(live, "active")).containsExactly(0, 2, 1, 0);
        assertThat(perBandList(live, "heard")).containsExactly(1, 2, 0, 0);
    }

    @Test
    void outOfRangeBandIndicesAreIgnored() {
        var live = new SimulationService.LiveSimulation("sim_test", 3);
        live.record(frame(0, List.of(-1, 0, 3, 99), List.of(-5, 2, 3), List.of(1, 100)));

        assertThat(perBandList(live, "looks")).containsExactly(1, 0, 0);
        assertThat(perBandList(live, "active")).containsExactly(0, 0, 1);
        assertThat(perBandList(live, "heard")).containsExactly(0, 1, 0);
    }

    @Test
    void snapshotListsAreCopies() {
        var live = new SimulationService.LiveSimulation("sim_test", 2);
        live.record(frame(0, List.of(0), List.of(0), List.of(0)));

        perBandList(live, "looks").set(0, 999);
        perBandList(live, "active").add(999);
        perBandList(live, "heard").clear();

        // Mutating the returned lists must not leak into later snapshots.
        assertThat(perBandList(live, "looks")).containsExactly(1, 0);
        assertThat(perBandList(live, "active")).containsExactly(1, 0);
        assertThat(perBandList(live, "heard")).containsExactly(1, 0);
    }

    @Test
    void snapshotBeforeAnyStepIsAllZero() {
        var live = new SimulationService.LiveSimulation("sim_test", 3);

        assertThat(perBandList(live, "looks")).containsExactly(0, 0, 0);
        assertThat(perBandList(live, "active")).containsExactly(0, 0, 0);
        assertThat(perBandList(live, "heard")).containsExactly(0, 0, 0);
    }

    @Test
    void oneArgConstructorOmitsPerBand() {
        var live = new SimulationService.LiveSimulation("sim_test");
        live.record(frame(0, List.of(0), List.of(0), List.of(0)));

        assertThat(live.snapshot()).doesNotContainKey("per_band");
    }

    @Test
    void usefulCountsOnlyScannedAndActiveBands() {
        var live = new SimulationService.LiveSimulation("sim_test", 6);
        live.record(frame(0, List.of(1, 2), List.of(2, 5), List.of(1)));

        // Only band 2 was both scanned and transmitting; band 1 was heard but not
        // active, band 5 was active but never looked at.
        assertThat(perBandList(live, "useful")).containsExactly(0, 0, 1, 0, 0, 0);
    }

    @Test
    void usefulAccumulatesAndIgnoresOutOfRange() {
        var live = new SimulationService.LiveSimulation("sim_test", 3);
        live.record(frame(0, List.of(-1, 0, 3, 99), List.of(-5, 0, 2, 3), List.of(0)));
        live.record(frame(1, List.of(0, 1), List.of(1, 2), List.of(1)));

        // Step 0: only band 0 is in range on both sides. Step 1: only band 1.
        assertThat(perBandList(live, "useful")).containsExactly(1, 1, 0);
    }

    @Test
    void usefulSnapshotIsCopyAfterHeard() {
        var live = new SimulationService.LiveSimulation("sim_test", 2);
        live.record(frame(0, List.of(0), List.of(0), List.of(0)));

        Map<String, Object> perBand =
                (Map<String, Object>) live.snapshot().get("per_band");
        assertThat(perBand.keySet()).containsExactly("looks", "active", "heard", "useful");

        perBandList(live, "useful").set(0, 999);
        perBandList(live, "useful").add(999);

        // Mutating the returned list must not leak into later snapshots.
        assertThat(perBandList(live, "useful")).containsExactly(1, 0);
    }

    @Test
    void oneArgConstructorStillOmitsPerBandWithUseful() {
        var live = new SimulationService.LiveSimulation("sim_test");
        live.record(frame(0, List.of(0, 1), List.of(0, 1), List.of(0)));

        assertThat(live.snapshot()).doesNotContainKey("per_band");
    }
}

package com.rfscheduler.simulation;

import com.rfscheduler.receiver.ReceiverConfig;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * The seven scenarios of PRD Section 13, transcribed exactly.
 *
 * <p>These mirror Ai-ml-1's {@code ml/experiments/scenario_*.yaml} - the same bands, emitters,
 * duration and mix - so a policy trained there is evaluated here on the same problem.
 *
 * <p>"X% of one class, Y% mixed" spreads the mixed remainder evenly over the other four classes.
 */
public final class ScenarioLibrary {

    private ScenarioLibrary() {
    }

    public static final List<String> IDS = List.of("A", "B", "C", "D", "E", "F", "G");

    private static Map<String, Double> mix(String dominant, double share) {
        Map<String, Double> m = new LinkedHashMap<>();
        double rest = dominant == null ? 0.2 : (1.0 - share) / 4.0;
        for (String c : EmitterBehavior.CLASSES) {
            m.put(c, c.equals(dominant) ? share : rest);
        }
        return m;
    }

    private static ReceiverConfig receiver() {
        return ReceiverConfig.defaults();
    }

    public static Scenario byId(String scenarioId) {
        String id = scenarioId == null ? "" : scenarioId.trim().toUpperCase();
        return switch (id) {
            case "A" -> new Scenario("A", "A - Mostly Fixed", 16, 10, 2000, 20, 42,
                    mix("fixed", 0.80), 0.25, receiver(), Map.of(),
                    "Baseline and ML should both do well; ML must still win on intercept time by "
                            + "not wasting dwell on quiet bands.");
            case "B" -> new Scenario("B", "B - Mostly Periodic", 16, 10, 2000, 20, 42,
                    mix("periodic", 0.70), 0.25, receiver(), Map.of(),
                    "The headline scenario. Round-robin systematically polls periodic bands in "
                            + "their OFF phase; periodicity features should cut detection latency "
                            + "(PRD DoD item 8).");
            case "C" -> new Scenario("C", "C - Frequency-Agile", 24, 12, 2000, 20, 42,
                    mix("agile", 0.70), 0.25, receiver(), Map.of(),
                    "Hopping emitters punish any fixed pattern; ML should track hop sets via the "
                            + "detection-rate EWMA.");
            case "D" -> new Scenario("D", "D - Mixed Environment", 24, 15, 3000, 20, 42,
                    mix(null, 0), 0.25, receiver(), Map.of(),
                    "Even split across all five classes; the generalisation check.");
            case "E" -> new Scenario("E", "E - High-Density", 32, 30, 3000, 20, 42,
                    mix(null, 0), 0.25, receiver(), Map.of(),
                    "Many emitters, so most bands are active; the gap to baseline narrows and "
                            + "Pfa/efficiency matter more than Pd.");
            case "F" -> new Scenario("F", "F - Sparse", 32, 5, 2000, 20, 42,
                    mix(null, 0), 0.25, receiver(), Map.of(),
                    "Few emitters over many bands; the largest expected win for a learned policy.");
            case "G" -> new Scenario("G", "G - Rapidly Changing", 24, 15, 3000, 20, 42,
                    mix(null, 0), 0.25, receiver(),
                    Map.of(
                            "agile", Map.of("hop_rate", 3),
                            "intermittent", Map.of("p_on_to_off", 0.4, "p_off_to_on", 0.12),
                            "periodic", Map.of("jitter", 4)),
                    "Dynamic behavior-class switching; tests whether the policy re-adapts rather "
                            + "than locking onto stale band estimates.");
            default -> throw new IllegalArgumentException(
                    "unknown scenario '" + scenarioId + "'; expected one of " + IDS);
        };
    }

    public static List<Scenario> all() {
        return IDS.stream().map(ScenarioLibrary::byId).toList();
    }
}

package com.rfscheduler.simulation;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import org.junit.jupiter.api.Test;

class SwitchingScenarioTest {

    private static List<Emitter> emitters(Scenario scenario, Random rng) {
        return EmitterFactory.build(scenario.emitters(), scenario.bands(),
                scenario.emitterMix(), rng, scenario.highPriorityFraction(),
                scenario.emitterParams());
    }

    @Test
    void gSwitchesClassesAndPreservesHomeBandAndClassParameters() {
        Scenario scenario = ScenarioLibrary.byId("G");
        Random rng = new Random(99);
        List<Emitter> emitters = emitters(scenario, rng);
        GroundTruth truth = new Spectrum(scenario.bands()).generate(
                emitters, scenario.durationSteps(), rng);
        assertThat(truth.duration()).isEqualTo(3000);
        Map<String, Integer> initialCounts = new HashMap<>();
        for (Emitter emitter : emitters) {
            initialCounts.merge(emitter.behaviorClass(), 1, Integer::sum);
            List<Emitter.Regime> regimes = emitter.switching().regimes();
            assertThat(regimes.size()).isGreaterThanOrEqualTo(2);
            assertThat(regimes.get(0).start()).isZero();
            assertThat(regimes.get(0).behaviorClass()).isEqualTo(emitter.behaviorClass());
            assertThat(regimes.get(0).params()).isEqualTo(emitter.params());
            assertThat(regimes.get(0).bands()).containsExactly(emitter.bands());
            assertThat(regimes.get(regimes.size() - 1).end()).isEqualTo(3000);
            for (int i = 0; i < regimes.size(); i++) {
                Emitter.Regime regime = regimes.get(i);
                assertThat(regime.bands()[0]).isEqualTo(emitter.primaryBand());
                if (!regime.behaviorClass().equals("agile")) {
                    assertThat(regime.bands()).containsExactly(emitter.primaryBand());
                }
                if (regime.behaviorClass().equals("agile")) {
                    assertThat(regime.params().get("hop_rate")).isEqualTo(3);
                }
                if (regime.behaviorClass().equals("intermittent")) {
                    assertThat(regime.params().get("p_on_to_off")).isEqualTo(0.4);
                    assertThat(regime.params().get("p_off_to_on")).isEqualTo(0.12);
                }
                if (regime.behaviorClass().equals("periodic")) {
                    assertThat(regime.params().get("jitter")).isEqualTo(4);
                }
                if (i > 0) {
                    Emitter.Regime previous = regimes.get(i - 1);
                    assertThat(regime.start()).isEqualTo(previous.end());
                    assertThat(regime.behaviorClass()).isNotEqualTo(previous.behaviorClass());
                }
            }
        }
        for (String behavior : EmitterBehavior.CLASSES) {
            assertThat(initialCounts.get(behavior)).isEqualTo(3);
        }
    }

    @Test
    void gRegimesHaveClassSpecificActivityRates() {
        Scenario scenario = ScenarioLibrary.byId("G");
        Random rng = new Random(99);
        List<Emitter> emitters = emitters(scenario, rng);
        Map<String, List<Double>> rates = new HashMap<>();
        for (String behavior : EmitterBehavior.CLASSES) {
            rates.put(behavior, new ArrayList<>());
        }
        for (Emitter emitter : emitters) {
            int[] track = EmitterBehavior.activityTrack(emitter, 3000, rng);
            for (Emitter.Regime regime : emitter.switching().regimes()) {
                int length = regime.end() - regime.start();
                if (length < 200) {
                    continue;
                }
                int active = 0;
                for (int t = regime.start(); t < regime.end(); t++) {
                    if (track[t] >= 0) {
                        active++;
                    }
                }
                rates.get(regime.behaviorClass()).add((double) active / length);
            }
        }
        double fixed = mean(rates.get("fixed"));
        double agile = mean(rates.get("agile"));
        double periodic = mean(rates.get("periodic"));
        double random = mean(rates.get("random"));
        double intermittent = mean(rates.get("intermittent"));
        assertThat(fixed).isBetween(0.90, 1.0);
        assertThat(agile).isBetween(0.85, 0.95);
        assertThat(periodic).isBetween(0.12, 0.27);
        assertThat(random).isBetween(0.10, 0.22);
        assertThat(intermittent).isBetween(0.16, 0.32);
    }

    @Test
    void nonSwitchingScenariosRemainDeterministic() {
        for (String id : List.of("A", "B", "C", "D", "E", "F")) {
            Scenario scenario = ScenarioLibrary.byId(id);
            GroundTruth first = generate(scenario, 99);
            GroundTruth second = generate(scenario, 99);
            assertThat(first.occupancyRate()).isEqualTo(second.occupancyRate());
            for (int t = 0; t < scenario.durationSteps(); t++) {
                assertThat(first.occupancyAt(t)).containsExactly(second.occupancyAt(t));
            }
            assertThat(first.emitters()).allSatisfy(
                    emitter -> assertThat(emitter.switching()).isNull());
        }
    }

    @Test
    void reportsFiveSeedGStatistics() {
        Scenario scenario = ScenarioLibrary.byId("G");
        double occupancy = 0;
        double switches = 0;
        for (long seed = 42; seed < 47; seed++) {
            Random rng = new Random(seed);
            List<Emitter> emitters = emitters(scenario, rng);
            GroundTruth truth = new Spectrum(scenario.bands()).generate(
                    emitters, scenario.durationSteps(), rng);
            occupancy += truth.occupancyRate();
            switches += emitters.stream().mapToInt(
                    e -> e.switching().regimes().size() - 1).average().orElseThrow();
        }
        System.out.printf("G_JAVA_5_SEED occupancy=%.6f switches_per_emitter=%.6f%n",
                occupancy / 5, switches / 5);
        assertThat(switches / 5).isGreaterThan(2);
    }

    private static GroundTruth generate(Scenario scenario, long seed) {
        Random rng = new Random(seed);
        return new Spectrum(scenario.bands()).generate(
                emitters(scenario, rng), scenario.durationSteps(), rng);
    }

    private static double mean(List<Double> values) {
        assertThat(values).isNotEmpty();
        return values.stream().mapToDouble(Double::doubleValue).average().orElseThrow();
    }
}

package com.rfscheduler.simulation;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;

/**
 * Builds a scenario's emitter population from a behavior-class mix (PRD Section 13).
 *
 * <p>Counts are allocated largest-remainder style so the requested proportions are hit exactly
 * rather than drifting with rounding - a scenario specified as "80% fixed" must actually contain
 * 80% fixed emitters or the comparison is not testing what it says it is.
 */
public final class EmitterFactory {

    private EmitterFactory() {
    }

    public static List<Emitter> build(
            int numEmitters,
            int numBands,
            Map<String, Double> mix,
            Random rng,
            double highPriorityFraction,
            Map<String, Map<String, Object>> paramsByClass) {

        List<String> classes = allocateClasses(numEmitters, mix);
        List<Emitter> emitters = new ArrayList<>(numEmitters);

        for (int i = 0; i < classes.size(); i++) {
            String behavior = classes.get(i);
            Map<String, Object> params = new HashMap<>(
                    paramsByClass == null
                            ? Map.of()
                            : paramsByClass.getOrDefault(behavior, Map.of()));
            int[] bands = assignBands(behavior, numBands, rng, params);
            double priority = rng.nextDouble() < highPriorityFraction ? 2.0 : 1.0;
            emitters.add(new Emitter(i, behavior, bands, priority,
                    randomiseParams(behavior, params, rng)));
        }
        return emitters;
    }

    static List<String> allocateClasses(int numEmitters, Map<String, Double> mix) {
        Set<String> unknown = new HashSet<>(mix.keySet());
        unknown.removeAll(EmitterBehavior.CLASSES);
        if (!unknown.isEmpty()) {
            throw new IllegalArgumentException("unknown behavior classes in mix: " + unknown);
        }
        double total = mix.values().stream().mapToDouble(Double::doubleValue).sum();
        if (total <= 0) {
            throw new IllegalArgumentException("emitter mix proportions must sum to a positive value");
        }

        Map<String, Double> exact = new LinkedHashMap<>();
        Map<String, Integer> counts = new LinkedHashMap<>();
        for (Map.Entry<String, Double> e : mix.entrySet()) {
            double share = numEmitters * e.getValue() / total;
            exact.put(e.getKey(), share);
            counts.put(e.getKey(), (int) share);
        }

        int allocated = counts.values().stream().mapToInt(Integer::intValue).sum();
        List<String> order = new ArrayList<>(exact.keySet());
        order.sort(Comparator
                .comparingDouble((String k) -> -(exact.get(k) - counts.get(k)))
                .thenComparingInt(EmitterBehavior.CLASSES::indexOf));
        for (int i = 0; i < numEmitters - allocated; i++) {
            String k = order.get(i % order.size());
            counts.put(k, counts.get(k) + 1);
        }

        List<String> classes = new ArrayList<>(numEmitters);
        for (String name : EmitterBehavior.CLASSES) {   // stable order regardless of map ordering
            for (int i = 0; i < counts.getOrDefault(name, 0); i++) {
                classes.add(name);
            }
        }
        return classes;
    }

    private static int[] assignBands(
            String behavior, int numBands, Random rng, Map<String, Object> params) {
        if ("agile".equals(behavior)) {
            int requested = params.get("hop_set_size") instanceof Number n
                    ? n.intValue() : Math.min(4, numBands);
            int size = Math.max(2, Math.min(requested, numBands));
            List<Integer> pool = new ArrayList<>();
            for (int b = 0; b < numBands; b++) {
                pool.add(b);
            }
            java.util.Collections.shuffle(pool, rng);
            int[] bands = new int[size];
            for (int i = 0; i < size; i++) {
                bands[i] = pool.get(i);
            }
            return bands;
        }
        return new int[] {rng.nextInt(numBands)};
    }

    private static Map<String, Object> randomiseParams(
            String behavior, Map<String, Object> params, Random rng) {
        Map<String, Object> out = new HashMap<>(params);
        switch (behavior) {
            case "periodic" -> {
                out.putIfAbsent("period", 12 + rng.nextInt(29));
                int period = ((Number) out.get("period")).intValue();
                out.putIfAbsent("on_duration", Math.max(1, (int) (period * 0.2)));
                out.putIfAbsent("phase", rng.nextInt(period));
            }
            case "agile" -> {
                out.putIfAbsent("hop_rate", 3 + rng.nextInt(8));
                out.putIfAbsent("hop_offset", rng.nextInt(5));
            }
            case "random" -> out.putIfAbsent("p_active", 0.05 + rng.nextDouble() * 0.20);
            case "intermittent" -> {
                out.putIfAbsent("p_on_to_off", 0.15 + rng.nextDouble() * 0.20);
                out.putIfAbsent("p_off_to_on", 0.03 + rng.nextDouble() * 0.07);
            }
            default -> {
                // fixed: duty defaults inside EmitterBehavior
            }
        }
        return out;
    }
}

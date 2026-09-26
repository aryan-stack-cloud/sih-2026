package com.rfscheduler.simulation;

import static org.assertj.core.api.Assertions.assertThat;

import com.rfscheduler.receiver.DetectionEngine;
import com.rfscheduler.receiver.Observation;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;
import org.junit.jupiter.api.Test;

class CollidingEmittersTest {

    @Test
    void cochannelDetectionCreditsEveryTransmitterButKeepsPriorityOwner() {
        List<Emitter> emitters = List.of(
                new Emitter(10, "fixed", new int[] {0}, 2.0, Map.of("duty", 1.0)),
                new Emitter(11, "fixed", new int[] {0}, 1.0, Map.of("duty", 1.0)));
        GroundTruth truth = new Spectrum(1).generate(emitters, 1, new Random(1));

        assertThat(truth.emittersPresent()).isEqualTo(Set.of(10L, 11L));
        assertThat(truth.priorityAt(0, 0)).isEqualTo(2.0);
        var observation = new Observation(0, List.of(0), Map.of(0, 3.0), true, false, 1.0);
        var outcome = new DetectionEngine(1.5).evaluate(observation, truth);
        assertThat(outcome.detectedEmitters()).isEqualTo(Set.of(10L, 11L));
    }
}

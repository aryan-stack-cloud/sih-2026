package com.rfscheduler.ml;

import static org.assertj.core.api.Assertions.assertThat;

import com.rfscheduler.receiver.Receiver;
import com.rfscheduler.receiver.ReceiverConfig;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class StateBuilderThreatAwareTest {

    private static List<Double> weights(StateBuilder builder, int numBands) {
        Receiver receiver = new Receiver(ReceiverConfig.defaults(), numBands);
        Map<String, Object> state = builder.toContract(receiver);
        @SuppressWarnings("unchecked")
        List<Map<String, Object>> bands = (List<Map<String, Object>>) state.get("bands");
        return bands.stream()
                .map(band -> ((Number) band.get("band_priority_weight")).doubleValue())
                .toList();
    }

    @Test
    void initialWeightsAreNeutral() {
        assertThat(weights(new StateBuilder(4), 4)).containsExactly(1.0, 1.0, 1.0, 1.0);
    }

    @Test
    void observeThenDecayMovesWeightHalfwayBackToNeutral() {
        StateBuilder builder = new StateBuilder(4);
        builder.observePriority(2, 2.0);
        builder.decayPriorityWeights(0.5);

        assertThat(weights(builder, 4)).containsExactly(1.0, 1.0, 1.5, 1.0);
    }

    @Test
    void resetRestoresNeutralWeights() {
        StateBuilder builder = new StateBuilder(4);
        builder.observePriority(1, 2.0);
        builder.observePriority(3, 2.0);

        builder.reset();

        assertThat(weights(builder, 4)).containsExactly(1.0, 1.0, 1.0, 1.0);
    }

    @Test
    void priorityBelowNeutralIsIgnored() {
        StateBuilder builder = new StateBuilder(4);
        builder.observePriority(0, 0.0);
        builder.observePriority(1, 0.5);

        assertThat(weights(builder, 4)).containsExactly(1.0, 1.0, 1.0, 1.0);
    }
}

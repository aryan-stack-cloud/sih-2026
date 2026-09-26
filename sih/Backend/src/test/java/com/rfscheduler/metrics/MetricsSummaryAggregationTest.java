package com.rfscheduler.metrics;

import static org.assertj.core.api.Assertions.assertThat;

import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;

class MetricsSummaryAggregationTest {

    @Test
    void poolsEmitterAndPriorityCountsAndExposesLatencyMedian() {
        MetricsSummary first = summary(1, 1, 1, 2, 2.0);
        MetricsSummary second = summary(1, 10, 2, 4, 8.0);

        Map<String, Object> pooled = MetricsSummary.aggregate(List.of(first, second));

        assertThat(pooled).containsEntry("interception_ratio", 2.0 / 11.0)
                .containsEntry("emitters_detected", 2)
                .containsEntry("emitters_present", 11)
                .containsEntry("tp_high_priority", 3)
                .containsEntry("fn_high_priority", 6)
                .containsEntry("hpdr", 1.0 / 3.0)
                .containsEntry("median_latency", 5.0);
        assertThat(first.asMap()).containsEntry("tp_high_priority", 1)
                .containsEntry("fn_high_priority", 2)
                .containsEntry("emitters_detected", 1)
                .containsEntry("emitters_present", 1);
    }

    private static MetricsSummary summary(int detected, int present, int tpHigh, int fnHigh,
                                          double latency) {
        return new MetricsSummary(0.5, 0.0, latency, latency, 0.0, latency,
                (double) detected / present, 0.5, 1.0, 1.0, 0.5, 0.5, 0.5, 0.5,
                1, 1, 0, 1, tpHigh, fnHigh, 1, 2, 1, 0, 0, 1, 2,
                0.5, detected, present);
    }
}

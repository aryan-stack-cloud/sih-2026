package com.rfscheduler.ml;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.rfscheduler.config.MlProperties;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.web.client.RestTemplate;

class DecisionExplanationTest {

    private static MlSchedulerClient clientWithDecideData(Map<String, Object> data) {
        RestTemplate rest = mock(RestTemplate.class);
        when(rest.postForObject(anyString(), any(), eq(Map.class)))
                .thenReturn(Map.of("data", data));
        return new MlSchedulerClient(rest,
                new MlProperties("http://localhost:8500", "http://localhost:8600", 100, 100,
                        true));
    }

    private static Map<String, Object> decideData(Map<String, Object> breakdown,
            String decisionSource) {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("action", Map.of("next_band", 3));
        data.put("model_id", "model_X");
        data.put("decision_id", "decision_9");
        if (breakdown != null) {
            data.put("index_breakdown", breakdown);
        }
        if (decisionSource != null) {
            data.put("decision_source", decisionSource);
        }
        return data;
    }

    @Test
    void decideCarriesBreakdownAndSource() {
        Map<String, Object> breakdown = new LinkedHashMap<>();
        breakdown.put("value", 0.5);
        breakdown.put("information", 0.2);
        breakdown.put("novelty", 0.1);
        breakdown.put("deadline", 0.15);
        breakdown.put("elapsed_s", 0.05);
        var client = clientWithDecideData(decideData(breakdown, "index"));

        ScanDecision decision = client.decide("sim_test", Map.of("bands", List.of()), "index",
                null, "A");

        assertThat(decision.decisionSource()).isEqualTo("index");
        assertThat(decision.indexBreakdown())
                .containsEntry("value", 0.5)
                .containsEntry("information", 0.2)
                .containsEntry("novelty", 0.1)
                .containsEntry("deadline", 0.15)
                .containsEntry("elapsed_s", 0.05)
                .hasSize(5);
    }

    @Test
    void decideWithoutExplanationYieldsNulls() {
        var client = clientWithDecideData(decideData(null, null));

        ScanDecision decision = client.decide("sim_test", Map.of("bands", List.of()), "index",
                null, "A");

        assertThat(decision.decisionSource()).isNull();
        assertThat(decision.indexBreakdown()).isNull();
    }

    @Test
    void decideSkipsNonNumericBreakdownEntries() {
        Map<String, Object> breakdown = new LinkedHashMap<>();
        breakdown.put("value", 0.5);
        breakdown.put("note", "not-a-number");
        var client = clientWithDecideData(decideData(breakdown, "index"));

        ScanDecision decision = client.decide("sim_test", Map.of("bands", List.of()), "index",
                null, "A");

        assertThat(decision.indexBreakdown())
                .containsEntry("value", 0.5)
                .hasSize(1);
    }

    @Test
    void fiveArgumentConstructorAndLocalFactoryLeaveNulls() {
        assertThat(new ScanDecision(3, null, "m", "id", true).indexBreakdown()).isNull();
        assertThat(new ScanDecision(3, null, "m", "id", true).decisionSource()).isNull();
        assertThat(ScanDecision.local(3, "round_robin").indexBreakdown()).isNull();
        assertThat(ScanDecision.local(3, "round_robin").decisionSource()).isNull();
    }
}

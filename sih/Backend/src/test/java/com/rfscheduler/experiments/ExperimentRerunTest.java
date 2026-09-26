package com.rfscheduler.experiments;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.rfscheduler.domain.ExperimentEntity;
import com.rfscheduler.exception.ApiException;
import com.rfscheduler.repository.ExperimentRepository;
import com.rfscheduler.service.SimulationRunner;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.core.task.TaskExecutor;

class ExperimentRerunTest {

    @Test
    void rerunClearsResultsAndOldWorkerCannotPersistIntoNewInvocation() {
        ExperimentEntity entity = new ExperimentEntity();
        entity.setId("exp_test");
        entity.setScenario("A");
        entity.setPoliciesCsv("baseline");
        entity.setEpisodes(1);
        entity.setSeed(42);
        entity.setStatus("completed");
        entity.setResultsJson("{\"old\":true}");
        ExperimentRepository repository = mock(ExperimentRepository.class);
        when(repository.findById("exp_test")).thenReturn(Optional.of(entity));
        when(repository.save(any(ExperimentEntity.class))).thenAnswer(call -> call.getArgument(0));
        List<Runnable> jobs = new ArrayList<>();
        TaskExecutor executor = jobs::add;
        ExperimentService service = new ExperimentService(repository, mock(SimulationRunner.class),
                executor);
        try {
            service.run("exp_test", null, null);
            assertThat(entity.getResultsJson()).isNull();
            assertThatThrownBy(() -> service.results("exp_test"))
                    .isInstanceOfSatisfying(ApiException.class,
                            error -> assertThat(error.code()).isEqualTo("EXPERIMENT_NOT_COMPLETE"));

            service.stop("exp_test");
            service.run("exp_test", null, null);
            jobs.get(0).run();

            assertThat(entity.getStatus()).isEqualTo("running");
            assertThat(entity.getResultsJson()).isNull();
            assertThat(service.progress("exp_test").asMap()).containsEntry("finished", false);
        } finally {
            service.shutdownEpisodeExecutor();
        }
    }

    @Test
    void fullFallbackComparisonHasStatusAndNoMetricDeltas() {
        ExperimentService service = new ExperimentService(mock(ExperimentRepository.class),
                mock(SimulationRunner.class), command -> { });
        try {
            Map<String, Object> unavailable = Map.of("ml_decisions", 0,
                    "fallback_decisions", 4,
                    "unavailable_reason", "dqn has no trained model for scenario A (16 bands)");
            @SuppressWarnings("unchecked")
            Map<String, Object> comparison = (Map<String, Object>) service.compare(
                    Map.of("baseline", Map.of(), "dqn", unavailable)).get("dqn");
            assertThat(comparison).containsOnly(
                    org.assertj.core.api.Assertions.entry("status", "fell_back_to_sweep"),
                    org.assertj.core.api.Assertions.entry("reason",
                            "dqn has no trained model for scenario A (16 bands)"));
        } finally {
            service.shutdownEpisodeExecutor();
        }
    }
}

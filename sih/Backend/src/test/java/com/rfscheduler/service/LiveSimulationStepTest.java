package com.rfscheduler.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.rfscheduler.config.SimulationProperties;
import com.rfscheduler.domain.SimulationEntity;
import com.rfscheduler.exception.ApiException;
import com.rfscheduler.ml.MlPeriodicityClient;
import com.rfscheduler.ml.MlSchedulerClient;
import com.rfscheduler.repository.SimulationRepository;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.junit.jupiter.api.Test;
import org.springframework.core.task.TaskExecutor;

class LiveSimulationStepTest {

    @Test
    void currentStepCountsProcessedFrames() {
        var live = new SimulationService.LiveSimulation("sim_test");
        live.record(new SimulationRunner.StepFrame(0, 0, List.of(0), List.of(),
                List.of(), List.of(), 0.0, Map.of(), null, true));
        assertThat(live.currentStep()).isEqualTo(1);
        live.record(new SimulationRunner.StepFrame(9, 0, List.of(0), List.of(),
                List.of(), List.of(), 0.0, Map.of(), null, true));
        assertThat(live.currentStep()).isEqualTo(10);
    }

    @Test
    void activeWorkerBlocksResetAndDeleteEvenAfterStop() {
        SimulationEntity entity = new SimulationEntity();
        entity.setId("sim_test");
        entity.setName("test");
        entity.setBands(16);
        entity.setDurationSteps(10);
        entity.setPolicyType("baseline");
        entity.setScenarioId("A");
        entity.setStatus("draft");
        SimulationRepository repository = mock(SimulationRepository.class);
        when(repository.findById("sim_test")).thenReturn(Optional.of(entity));
        when(repository.save(any(SimulationEntity.class))).thenAnswer(call -> call.getArgument(0));
        List<Runnable> jobs = new ArrayList<>();
        TaskExecutor executor = jobs::add;
        var service = new SimulationService(repository, mock(SimulationRunner.class),
                mock(MlSchedulerClient.class), mock(MlPeriodicityClient.class), executor,
                new SimulationProperties(5, 500, 4));

        service.start("sim_test", null);
        service.stop("sim_test");
        assertThatThrownBy(() -> service.reset("sim_test"))
                .isInstanceOfSatisfying(ApiException.class,
                        error -> assertThat(error.code()).isEqualTo("SIMULATION_RUNNING"));
        assertThatThrownBy(() -> service.delete("sim_test"))
                .isInstanceOfSatisfying(ApiException.class,
                        error -> assertThat(error.code()).isEqualTo("SIMULATION_RUNNING"));
        assertThat(jobs).hasSize(1);
    }
}

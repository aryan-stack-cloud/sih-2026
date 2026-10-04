package com.rfscheduler.controller;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import com.rfscheduler.config.SimulationProperties;
import com.rfscheduler.domain.ExperimentEntity;
import com.rfscheduler.domain.SimulationEntity;
import com.rfscheduler.dto.Requests;
import com.rfscheduler.experiments.ExperimentService;
import com.rfscheduler.ml.MlPeriodicityClient;
import com.rfscheduler.ml.MlSchedulerClient;
import com.rfscheduler.repository.ExperimentRepository;
import com.rfscheduler.repository.SimulationRepository;
import com.rfscheduler.service.SimulationRunner;
import com.rfscheduler.service.SimulationService;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import org.junit.jupiter.api.Test;
import tools.jackson.databind.json.JsonMapper;

class ThreatAwareControllerTest {

    private static final JsonMapper MAPPER = JsonMapper.builder().build();

    private static SimulationService simulationService() {
        SimulationRepository repository = mock(SimulationRepository.class);
        Map<String, SimulationEntity> store = new ConcurrentHashMap<>();
        when(repository.save(any(SimulationEntity.class))).thenAnswer(call -> {
            SimulationEntity entity = call.getArgument(0);
            store.put(entity.getId(), entity);
            return entity;
        });
        when(repository.findById(any(String.class))).thenAnswer(call ->
                Optional.ofNullable(store.get(call.getArgument(0))));
        return new SimulationService(repository, mock(SimulationRunner.class),
                mock(MlSchedulerClient.class), mock(MlPeriodicityClient.class),
                command -> command.run(),
                new SimulationProperties(5, 500, 4));
    }

    private static ExperimentService experimentService() {
        ExperimentRepository repository = mock(ExperimentRepository.class);
        Map<String, ExperimentEntity> store = new ConcurrentHashMap<>();
        when(repository.save(any(ExperimentEntity.class))).thenAnswer(call -> {
            ExperimentEntity entity = call.getArgument(0);
            store.put(entity.getId(), entity);
            return entity;
        });
        when(repository.findById(any(String.class))).thenAnswer(call ->
                Optional.ofNullable(store.get(call.getArgument(0))));
        return new ExperimentService(repository, mock(SimulationRunner.class),
                command -> command.run());
    }

    @Test
    void createSimulationWithoutThreatAwareDeserialisesToNull() throws Exception {
        String json = """
                {"name":"t","bands":16,"durationSteps":10,"scenario":"A","policy":"baseline"}""";

        Requests.CreateSimulation body = MAPPER.readValue(json, Requests.CreateSimulation.class);

        assertThat(body.threatAware()).isNull();
    }

    @Test
    void createSimulationWithThreatAwareTrueDeserialisesToTrue() throws Exception {
        String json = """
                {"name":"t","bands":16,"durationSteps":10,"scenario":"A","policy":"baseline",
                "threatAware":true}""";

        Requests.CreateSimulation body = MAPPER.readValue(json, Requests.CreateSimulation.class);

        assertThat(body.threatAware()).isTrue();
    }

    @Test
    void simulationSummaryReflectsStoredThreatAwareFlag() {
        SimulationService service = simulationService();

        SimulationEntity enabled = service.create(
                "threat", 16, 10, 42L, "A", "baseline", true);
        SimulationEntity def = service.create(
                "plain", 16, 10, 42L, "A", "baseline", null);

        assertThat(SimulationController.summary(service.get(enabled.getId())))
                .containsEntry("threat_aware", true);
        assertThat(SimulationController.summary(service.get(def.getId())))
                .containsEntry("threat_aware", false);
    }

    @Test
    void simulationUpdateAppliesThreatAwareOnlyWhenPresent() {
        SimulationService service = simulationService();
        SimulationEntity sim = service.create("t", 16, 10, 42L, "A", "baseline", null);

        service.update(sim.getId(), null, null, null, null, null, true);
        assertThat(SimulationController.summary(service.get(sim.getId())))
                .containsEntry("threat_aware", true);

        service.update(sim.getId(), null, null, null, null, null, null);
        assertThat(SimulationController.summary(service.get(sim.getId())))
                .containsEntry("threat_aware", true);
    }

    @Test
    void experimentSummaryReflectsStoredThreatAwareFlag() {
        ExperimentService service = experimentService();

        ExperimentEntity enabled = service.create(
                "threat", "A", List.of("baseline", "bandit"), 2, 42L, true);
        ExperimentEntity def = service.create(
                "plain", "A", List.of("baseline", "bandit"), 2, 42L, null);

        assertThat(ExperimentController.summary(service.get(enabled.getId())))
                .containsEntry("threat_aware", true);
        assertThat(ExperimentController.summary(service.get(def.getId())))
                .containsEntry("threat_aware", false);
    }
}

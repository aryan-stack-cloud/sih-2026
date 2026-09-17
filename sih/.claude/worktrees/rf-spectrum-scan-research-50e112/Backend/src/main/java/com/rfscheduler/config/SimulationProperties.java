package com.rfscheduler.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/** Simulation worker limits. */
@ConfigurationProperties(prefix = "rfscheduler.simulation")
public record SimulationProperties(
        int maxConcurrent,
        int checkpointEverySteps,
        int workerThreads) {

    public SimulationProperties {
        maxConcurrent = maxConcurrent <= 0 ? 5 : maxConcurrent;             // NFR-004
        checkpointEverySteps = checkpointEverySteps <= 0 ? 500 : checkpointEverySteps;  // NFR-005
        workerThreads = workerThreads <= 0 ? 4 : workerThreads;
    }
}

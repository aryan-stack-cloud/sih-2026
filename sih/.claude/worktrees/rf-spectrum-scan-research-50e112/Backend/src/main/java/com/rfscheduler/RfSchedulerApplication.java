package com.rfscheduler;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * Intelligent RF Spectrum Scan Strategy - Backend.
 *
 * <p>System of record and orchestrator: owns the simulation, calls Ai-ml-2 for periodicity and
 * Ai-ml-1 for scan decisions, computes the reward, and streams state to the Frontend.
 *
 * <p>Scope: simulation-only. No real RF hardware, no interception, no jamming, no weapon control.
 */
@SpringBootApplication
@EnableAsync
public class RfSchedulerApplication {
    public static void main(String[] args) {
        SpringApplication.run(RfSchedulerApplication.class, args);
    }
}

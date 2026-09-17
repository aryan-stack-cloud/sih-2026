package com.rfscheduler.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

/** A simulation run - the root aggregate (PRD Section 14.4). */
@Entity
@Table(name = "simulations")
public class SimulationEntity {

    @Id
    private String id;                    // "sim_<8-hex>", API_CONTRACT.md Section 6

    private String name;
    private long seed;
    private int bands;

    @Column(name = "duration_steps")
    private int durationSteps;

    private String status;                // draft|running|stopped|completed|failed

    @Column(name = "policy_type")
    private String policyType;

    @Column(name = "scenario_id")
    private String scenarioId;

    @Column(name = "current_step")
    private int currentStep;

    @Column(name = "created_at")
    private Instant createdAt;

    @Column(name = "updated_at")
    private Instant updatedAt;

    public String getId() {
        return id;
    }

    public void setId(String id) {
        this.id = id;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public long getSeed() {
        return seed;
    }

    public void setSeed(long seed) {
        this.seed = seed;
    }

    public int getBands() {
        return bands;
    }

    public void setBands(int bands) {
        this.bands = bands;
    }

    public int getDurationSteps() {
        return durationSteps;
    }

    public void setDurationSteps(int durationSteps) {
        this.durationSteps = durationSteps;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getPolicyType() {
        return policyType;
    }

    public void setPolicyType(String policyType) {
        this.policyType = policyType;
    }

    public String getScenarioId() {
        return scenarioId;
    }

    public void setScenarioId(String scenarioId) {
        this.scenarioId = scenarioId;
    }

    public int getCurrentStep() {
        return currentStep;
    }

    public void setCurrentStep(int currentStep) {
        this.currentStep = currentStep;
    }

    public Instant getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(Instant createdAt) {
        this.createdAt = createdAt;
    }

    public Instant getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(Instant updatedAt) {
        this.updatedAt = updatedAt;
    }
}

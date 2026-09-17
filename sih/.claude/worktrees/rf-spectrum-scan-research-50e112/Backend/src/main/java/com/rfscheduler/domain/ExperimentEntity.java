package com.rfscheduler.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.time.Instant;

/** An experiment: one scenario run under several policies for direct comparison (FR-009). */
@Entity
@Table(name = "experiments")
public class ExperimentEntity {

    @Id
    private String id;                     // "exp_<8-hex>"

    private String name;
    private String scenario;               // A..G

    @Column(name = "policies_csv")
    private String policiesCsv;

    private int episodes;
    private long seed;
    private String status;                 // draft|running|completed|failed|cancelled

    // Plain String, not @Lob: the migration declares TEXT, which both PostgreSQL and H2 report
    // as VARCHAR. Mapping it as a CLOB makes Hibernate's schema validation reject the column.
    @Column(name = "expected_outcome", columnDefinition = "TEXT")
    private String expectedOutcome;

    @Column(name = "results_json", columnDefinition = "TEXT")
    private String resultsJson;

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

    public String getScenario() {
        return scenario;
    }

    public void setScenario(String scenario) {
        this.scenario = scenario;
    }

    public String getPoliciesCsv() {
        return policiesCsv;
    }

    public void setPoliciesCsv(String policiesCsv) {
        this.policiesCsv = policiesCsv;
    }

    public int getEpisodes() {
        return episodes;
    }

    public void setEpisodes(int episodes) {
        this.episodes = episodes;
    }

    public long getSeed() {
        return seed;
    }

    public void setSeed(long seed) {
        this.seed = seed;
    }

    public String getStatus() {
        return status;
    }

    public void setStatus(String status) {
        this.status = status;
    }

    public String getExpectedOutcome() {
        return expectedOutcome;
    }

    public void setExpectedOutcome(String expectedOutcome) {
        this.expectedOutcome = expectedOutcome;
    }

    public String getResultsJson() {
        return resultsJson;
    }

    public void setResultsJson(String resultsJson) {
        this.resultsJson = resultsJson;
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

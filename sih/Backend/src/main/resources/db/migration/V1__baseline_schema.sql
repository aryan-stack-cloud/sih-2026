-- Core schema, PRD Section 14.4 / Backend README "Database schema".
-- Written in SQL that both PostgreSQL and H2 (PostgreSQL compatibility mode) accept, so the
-- default no-Docker profile and the docker profile share one set of migrations.

CREATE TABLE simulations (
    id              VARCHAR(32)  PRIMARY KEY,          -- "sim_<8-hex>" (API_CONTRACT.md Section 6)
    name            VARCHAR(255) NOT NULL,
    seed            BIGINT       NOT NULL,
    bands           INTEGER      NOT NULL,
    duration_steps  INTEGER      NOT NULL,
    status          VARCHAR(32)  NOT NULL,             -- draft|running|stopped|completed|failed
    policy_type     VARCHAR(32)  NOT NULL DEFAULT 'baseline',
    scenario_id     VARCHAR(8),
    current_step    INTEGER      NOT NULL DEFAULT 0,
    created_at      TIMESTAMP    NOT NULL,
    updated_at      TIMESTAMP    NOT NULL
);

CREATE TABLE emitters (
    id              BIGSERIAL    PRIMARY KEY,
    simulation_id   VARCHAR(32)  NOT NULL REFERENCES simulations(id) ON DELETE CASCADE,
    behavior_class  VARCHAR(32)  NOT NULL,             -- fixed|periodic|agile|random|intermittent
    band            INTEGER      NOT NULL,
    bands_csv       VARCHAR(255),                      -- hop set, for the agile class
    period_steps    INTEGER,
    on_duration     INTEGER,
    phase           INTEGER,
    priority        DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    params_json     TEXT
);
CREATE INDEX idx_emitters_simulation ON emitters(simulation_id);

CREATE TABLE receiver_configs (
    id              BIGSERIAL    PRIMARY KEY,
    simulation_id   VARCHAR(32)  NOT NULL REFERENCES simulations(id) ON DELETE CASCADE,
    bandwidth_k     INTEGER      NOT NULL DEFAULT 2,
    dwell_ms        INTEGER      NOT NULL DEFAULT 4,
    tuning_delay_ms INTEGER      NOT NULL DEFAULT 3,
    step_ms         INTEGER      NOT NULL DEFAULT 10,
    threshold       DOUBLE PRECISION NOT NULL DEFAULT 1.5,
    snr_mean        DOUBLE PRECISION NOT NULL DEFAULT 3.0,
    noise_sigma     DOUBLE PRECISION NOT NULL DEFAULT 1.0
);
CREATE INDEX idx_receiver_simulation ON receiver_configs(simulation_id);

CREATE TABLE scan_events (
    id              BIGSERIAL    PRIMARY KEY,
    simulation_id   VARCHAR(32)  NOT NULL REFERENCES simulations(id) ON DELETE CASCADE,
    t               INTEGER      NOT NULL,
    band            INTEGER      NOT NULL,
    policy_type     VARCHAR(32)  NOT NULL,
    dwell_used      INTEGER      NOT NULL,
    valid           BOOLEAN      NOT NULL DEFAULT TRUE,
    retuned         BOOLEAN      NOT NULL DEFAULT FALSE
);
CREATE INDEX idx_scan_events_simulation_t ON scan_events(simulation_id, t);

CREATE TABLE detection_events (
    id              BIGSERIAL    PRIMARY KEY,
    scan_event_id   BIGINT       NOT NULL REFERENCES scan_events(id) ON DELETE CASCADE,
    band            INTEGER      NOT NULL,
    type            VARCHAR(4)   NOT NULL,             -- TP|FN|FP|TN (API_CONTRACT.md Section 6)
    latency_ms      INTEGER,
    emitter_ref     BIGINT,
    priority        DOUBLE PRECISION NOT NULL DEFAULT 1.0
);
CREATE INDEX idx_detection_events_scan ON detection_events(scan_event_id);

CREATE TABLE scheduler_decisions (
    id              BIGSERIAL    PRIMARY KEY,
    scan_event_id   BIGINT       NOT NULL REFERENCES scan_events(id) ON DELETE CASCADE,
    simulation_id   VARCHAR(32)  NOT NULL,
    decision_id     VARCHAR(64),
    state_vector    TEXT,
    action_band     INTEGER      NOT NULL,
    dwell_time      INTEGER,
    reward          DOUBLE PRECISION NOT NULL DEFAULT 0,
    reward_terms    TEXT,
    model_id        VARCHAR(64)
);
CREATE INDEX idx_decisions_simulation ON scheduler_decisions(simulation_id);

CREATE TABLE models (
    id              VARCHAR(64)  PRIMARY KEY,          -- "model_<algorithm>_<8-hex>"
    algorithm       VARCHAR(32)  NOT NULL,
    version         INTEGER      NOT NULL DEFAULT 1,
    scenario        VARCHAR(8),
    hyperparams     TEXT,
    metrics         TEXT,
    active          BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMP    NOT NULL
);

CREATE TABLE experiments (
    id               VARCHAR(32)  PRIMARY KEY,         -- "exp_<8-hex>"
    name             VARCHAR(255) NOT NULL,
    scenario         VARCHAR(8)   NOT NULL,            -- A..G
    policies_csv     VARCHAR(255) NOT NULL,
    episodes         INTEGER      NOT NULL DEFAULT 20,
    seed             BIGINT       NOT NULL DEFAULT 42,
    status           VARCHAR(32)  NOT NULL,
    expected_outcome TEXT,
    results_json     TEXT,
    created_at       TIMESTAMP    NOT NULL,
    updated_at       TIMESTAMP    NOT NULL
);

CREATE TABLE audit_log (
    id         BIGSERIAL    PRIMARY KEY,
    actor      VARCHAR(128) NOT NULL,
    action     VARCHAR(128) NOT NULL,
    target     VARCHAR(128),
    detail     TEXT,
    created_at TIMESTAMP    NOT NULL
);

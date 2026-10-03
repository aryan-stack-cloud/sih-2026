package com.rfscheduler.service;

import static org.assertj.core.api.Assertions.assertThat;

import java.sql.DriverManager;
import org.flywaydb.core.Flyway;
import org.junit.jupiter.api.Test;

class SimulationModelMigrationTest {

    @Test
    void defaultH2SchemaAcceptsModelIdMigration() throws Exception {
        String url = "jdbc:h2:mem:model_id_migration;MODE=PostgreSQL;"
                + "DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1";
        var migration = Flyway.configure().dataSource(url, "sa", "")
                .locations("classpath:db/migration").load().migrate();
        assertThat(migration.migrationsExecuted).isEqualTo(3);
        try (var connection = DriverManager.getConnection(url, "sa", "");
              var statement = connection.createStatement();
              var result = statement.executeQuery("SELECT model_id FROM simulations WHERE 1 = 0")) {
            assertThat(result.getMetaData().getColumnCount()).isEqualTo(1);
        }
    }

    @Test
    void v3AddsThreatAwareToSimulationsAndExperiments() throws Exception {
        String url = "jdbc:h2:mem:threat_aware_migration;MODE=PostgreSQL;"
                + "DATABASE_TO_LOWER=TRUE;DB_CLOSE_DELAY=-1";
        Flyway.configure().dataSource(url, "sa", "")
                .locations("classpath:db/migration").load().migrate();
        try (var connection = DriverManager.getConnection(url, "sa", "");
              var statement = connection.createStatement()) {
            for (String table : new String[]{"simulations", "experiments"}) {
                try (var result = statement.executeQuery(
                        "SELECT threat_aware FROM " + table + " WHERE 1 = 0")) {
                    assertThat(result.getMetaData().getColumnCount()).as("%s", table).isEqualTo(1);
                }
                // The column defaults to false, so rows written before V3 read back threat-naive.
                statement.executeUpdate("INSERT INTO " + table + " ("
                        + ("simulations".equals(table)
                                ? "id, name, seed, bands, duration_steps, status, current_step, "
                                        + "created_at, updated_at"
                                : "id, name, scenario, policies_csv, status, created_at, "
                                        + "updated_at")
                        + ") VALUES ("
                        + ("simulations".equals(table)
                                ? "'sim_v3check', 'v3', 1, 16, 10, 'draft', 0, "
                                        + "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP"
                                : "'exp_v3check', 'v3', 'A', 'baseline', 'draft', "
                                        + "CURRENT_TIMESTAMP, CURRENT_TIMESTAMP")
                        + ")");
                try (var result = statement.executeQuery(
                        "SELECT threat_aware FROM " + table + " WHERE id = '"
                                + ("simulations".equals(table) ? "sim_v3check"
                                        : "exp_v3check") + "'")) {
                    assertThat(result.next()).as("%s row", table).isTrue();
                    assertThat(result.getBoolean(1)).as("%s default", table).isFalse();
                }
            }
        }
    }
}

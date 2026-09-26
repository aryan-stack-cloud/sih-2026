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
        assertThat(migration.migrationsExecuted).isEqualTo(2);
        try (var connection = DriverManager.getConnection(url, "sa", "");
             var statement = connection.createStatement();
             var result = statement.executeQuery("SELECT model_id FROM simulations WHERE 1 = 0")) {
            assertThat(result.getMetaData().getColumnCount()).isEqualTo(1);
        }
    }
}

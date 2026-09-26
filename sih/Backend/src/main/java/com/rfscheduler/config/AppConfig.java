package com.rfscheduler.config;

import java.time.Duration;
import java.net.http.HttpClient;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.http.client.JdkClientHttpRequestFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.core.task.TaskExecutor;
import org.springframework.scheduling.concurrent.ThreadPoolTaskExecutor;
import org.springframework.web.client.RestTemplate;

/**
 * Wiring for the ML HTTP clients and the simulation worker pool.
 *
 * <p>NOTE ON REDIS. The PRD uses Redis for WebSocket fan-out and the async job queue. Neither is
 * required for a single-instance deployment, and the demo profile runs without it: fan-out is
 * in-process (see WebSocketHub) and jobs run on the executor below. The Redis-backed
 * implementations belong behind the same interfaces when the system is scaled to multiple
 * instances - that is the point of ADR-06's service boundaries.
 */
@Configuration
@EnableConfigurationProperties({MlProperties.class, SimulationProperties.class})
public class AppConfig {

    @Bean
    public RestTemplate mlRestTemplate(MlProperties props) {
        // A shared HttpClient reuses localhost connections across the many per-step requests.
        // Opening a fresh socket for every call exhausted ephemeral ports during 10-episode sweeps.
        HttpClient client = HttpClient.newBuilder()
                .connectTimeout(Duration.ofMillis(props.connectTimeoutMs()))
                .version(HttpClient.Version.HTTP_1_1)
                .build();
        JdkClientHttpRequestFactory factory = new JdkClientHttpRequestFactory(client);
        factory.setReadTimeout(Duration.ofMillis(props.readTimeoutMs()));
        return new RestTemplate(factory);
    }

    @Bean("simulationExecutor")
    public TaskExecutor simulationExecutor(SimulationProperties props) {
        ThreadPoolTaskExecutor executor = new ThreadPoolTaskExecutor();
        executor.setCorePoolSize(props.workerThreads());
        executor.setMaxPoolSize(Math.max(props.workerThreads(), props.maxConcurrent()));
        executor.setQueueCapacity(64);
        executor.setThreadNamePrefix("sim-worker-");
        executor.initialize();
        return executor;
    }
}

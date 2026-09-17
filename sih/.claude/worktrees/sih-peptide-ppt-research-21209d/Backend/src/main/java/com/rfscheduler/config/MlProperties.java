package com.rfscheduler.config;

import org.springframework.boot.context.properties.ConfigurationProperties;

/** Connection settings for the two ML microservices (API_CONTRACT.md Sections 4, 5 and 7). */
@ConfigurationProperties(prefix = "rfscheduler.ml")
public record MlProperties(
        String schedulerUrl,
        String periodicityUrl,
        int connectTimeoutMs,
        int readTimeoutMs,
        boolean fallbackToBaseline) {

    public MlProperties {
        schedulerUrl = schedulerUrl == null ? "http://localhost:8500" : schedulerUrl;
        periodicityUrl = periodicityUrl == null ? "http://localhost:8600" : periodicityUrl;
        connectTimeoutMs = connectTimeoutMs <= 0 ? 2000 : connectTimeoutMs;
        readTimeoutMs = readTimeoutMs <= 0 ? 5000 : readTimeoutMs;
    }
}

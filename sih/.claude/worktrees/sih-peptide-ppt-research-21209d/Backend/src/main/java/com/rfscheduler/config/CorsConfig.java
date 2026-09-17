package com.rfscheduler.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * CORS for the Frontend dev server.
 *
 * <p>The Frontend runs on :5173 and the API on :8080 (API_CONTRACT.md Section 7), so every
 * browser call is cross-origin. Permissive by design for the MVP demo, which PRD Section 16
 * scopes to a trusted local network; tighten this alongside enabling auth.
 */
@Configuration
public class CorsConfig implements WebMvcConfigurer {

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
                .allowedOriginPatterns("*")
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                .allowedHeaders("*");
        registry.addMapping("/health").allowedOriginPatterns("*");
        registry.addMapping("/ready").allowedOriginPatterns("*");
    }
}

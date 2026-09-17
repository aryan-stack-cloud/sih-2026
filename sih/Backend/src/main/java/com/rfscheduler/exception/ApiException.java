package com.rfscheduler.exception;

import java.util.Map;
import org.springframework.http.HttpStatus;

/**
 * A domain error that maps onto the Section 1 error envelope.
 *
 * <p>Status/code pairings follow the contract: 404 with {@code RESOURCE_NOT_FOUND}, 422 with
 * {@code VALIDATION_ERROR}, 409 for state conflicts, 500 otherwise.
 */
public class ApiException extends RuntimeException {

    private final HttpStatus status;
    private final String code;
    private final Map<String, Object> details;

    public ApiException(HttpStatus status, String code, String message, Map<String, Object> details) {
        super(message);
        this.status = status;
        this.code = code;
        this.details = details == null ? Map.of() : details;
    }

    public static ApiException notFound(String resource, String id) {
        return new ApiException(HttpStatus.NOT_FOUND, "RESOURCE_NOT_FOUND",
                resource + " " + id + " not found", Map.of("id", id));
    }

    public static ApiException conflict(String code, String message) {
        return new ApiException(HttpStatus.CONFLICT, code, message, Map.of());
    }

    public static ApiException validation(String message, Map<String, Object> details) {
        return new ApiException(HttpStatus.UNPROCESSABLE_ENTITY, "VALIDATION_ERROR",
                message, details);
    }

    public static ApiException upstream(String service, String message) {
        return new ApiException(HttpStatus.BAD_GATEWAY, "ML_SERVICE_UNAVAILABLE",
                service + " is unavailable: " + message, Map.of("service", service));
    }

    public HttpStatus status() {
        return status;
    }

    public String code() {
        return code;
    }

    public Map<String, Object> details() {
        return details;
    }
}

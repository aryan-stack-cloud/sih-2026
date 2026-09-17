package com.rfscheduler.dto;

import com.fasterxml.jackson.annotation.JsonInclude;
import java.util.Map;
import java.util.UUID;

/**
 * The standard envelope of API_CONTRACT.md Section 1.
 *
 * <pre>
 *   { "success": true,  "data": { }, "requestId": "req_019a" }
 *   { "success": false, "error": { "code", "message", "details" }, "requestId": "req_019a" }
 * </pre>
 *
 * <p>Every public and internal response uses this, without exception - the Frontend and both ML
 * services all unwrap {@code data} the same way.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record ApiResponse<T>(
        boolean success,
        T data,
        ApiError error,
        String requestId) {

    public static String newRequestId() {
        return "req_" + UUID.randomUUID().toString().replace("-", "").substring(0, 8);
    }

    public static <T> ApiResponse<T> ok(T data) {
        return new ApiResponse<>(true, data, null, newRequestId());
    }

    public static <T> ApiResponse<T> ok(T data, String requestId) {
        return new ApiResponse<>(true, data, null,
                requestId == null ? newRequestId() : requestId);
    }

    public static <T> ApiResponse<T> fail(String code, String message, Map<String, Object> details) {
        return new ApiResponse<>(false, null,
                new ApiError(code, message, details == null ? Map.of() : details),
                newRequestId());
    }

    /** Error body of Section 1. */
    public record ApiError(String code, String message, Map<String, Object> details) {
    }
}

package com.rfscheduler.exception;

import com.rfscheduler.dto.ApiResponse;
import java.util.LinkedHashMap;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.servlet.resource.NoResourceFoundException;

/**
 * Maps every exception onto the Section 1 error envelope.
 *
 * <p>Contract rules, implemented literally: validation failures return 422 with
 * {@code VALIDATION_ERROR} and a field-to-message map in {@code details}; missing resources return
 * 404 with {@code RESOURCE_NOT_FOUND}; everything else gets a specific code and 409/500.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    @ExceptionHandler(ApiException.class)
    public ResponseEntity<ApiResponse<Void>> handleApi(ApiException e) {
        return ResponseEntity.status(e.status())
                .body(ApiResponse.fail(e.code(), e.getMessage(), e.details()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ApiResponse<Void>> handleBeanValidation(
            MethodArgumentNotValidException e) {
        Map<String, Object> details = new LinkedHashMap<>();
        for (FieldError fe : e.getBindingResult().getFieldErrors()) {
            details.put(fe.getField(), fe.getDefaultMessage());
        }
        return ResponseEntity.unprocessableEntity()
                .body(ApiResponse.fail("VALIDATION_ERROR", "Request failed validation", details));
    }

    @ExceptionHandler({
            MissingServletRequestParameterException.class,
            MethodArgumentTypeMismatchException.class,
            HttpMessageNotReadableException.class})
    public ResponseEntity<ApiResponse<Void>> handleMalformed(Exception e) {
        return ResponseEntity.unprocessableEntity()
                .body(ApiResponse.fail("VALIDATION_ERROR", "Request failed validation",
                        Map.of("reason", String.valueOf(e.getMessage()))));
    }

    @ExceptionHandler(IllegalArgumentException.class)
    public ResponseEntity<ApiResponse<Void>> handleIllegalArgument(IllegalArgumentException e) {
        // The simulation core validates with plain IllegalArgumentException; surface those as
        // validation failures rather than 500s, since they are caused by request content.
        return ResponseEntity.unprocessableEntity()
                .body(ApiResponse.fail("VALIDATION_ERROR", String.valueOf(e.getMessage()),
                        Map.of()));
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public ResponseEntity<ApiResponse<Void>> handleNoResource(NoResourceFoundException e) {
        return ResponseEntity.status(HttpStatus.NOT_FOUND)
                .body(ApiResponse.fail("RESOURCE_NOT_FOUND", "No such endpoint", Map.of()));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ApiResponse<Void>> handleUnexpected(Exception e) {
        log.error("unhandled error", e);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(ApiResponse.fail("INTERNAL_ERROR", "Unexpected server error", Map.of()));
    }
}

package com.rfscheduler.ml;

/** Ai-ml-1 has no registered model compatible with this decision request. */
public class NoCompatibleModelException extends RuntimeException {

    public NoCompatibleModelException(String message) {
        super(message);
    }
}

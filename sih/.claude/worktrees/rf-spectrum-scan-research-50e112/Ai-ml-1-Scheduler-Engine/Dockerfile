# Ai-ml-1 Scheduler Engine -- API_CONTRACT.md Section 7: container port 8500.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    ML_CHECKPOINT_DIR=/app/ml/checkpoints

WORKDIR /app

# Dependencies first so a source change does not invalidate the pip layer.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ml/ ./ml/
COPY scripts/ ./scripts/
COPY API_CONTRACT.md README.md ./

# Model artifacts are a named volume shared with the Backend (PRD Section 19.2).
VOLUME ["/app/ml/checkpoints"]

RUN useradd --create-home --uid 10001 mlrunner \
    && mkdir -p /app/ml/checkpoints \
    && chown -R mlrunner:mlrunner /app
USER mlrunner

EXPOSE 8500

HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8500/internal/health', timeout=2).status == 200 else 1)"

CMD ["uvicorn", "ml.api.main:app", "--host", "0.0.0.0", "--port", "8500"]

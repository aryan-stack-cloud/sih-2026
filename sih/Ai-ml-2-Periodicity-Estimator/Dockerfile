# Ai-ml-2 Periodicity Estimator -- API_CONTRACT.md Section 7: container port 8600.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY periodicity/ ./periodicity/
COPY API_CONTRACT.md README.md ./

RUN useradd --create-home --uid 10002 mlrunner && chown -R mlrunner:mlrunner /app
USER mlrunner

EXPOSE 8600

HEALTHCHECK --interval=15s --timeout=3s --start-period=15s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8600/internal/health', timeout=2).status == 200 else 1)"

CMD ["uvicorn", "periodicity.api.main:app", "--host", "0.0.0.0", "--port", "8600"]

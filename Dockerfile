FROM python:3.11-slim

# ------------------------------------------------------------------
# System packages
# ------------------------------------------------------------------
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libhts-dev \
        libbz2-dev \
        liblzma-dev \
        libcurl4-openssl-dev && \
    rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------------
# Python dependencies
# ------------------------------------------------------------------
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# ------------------------------------------------------------------
# Application code
# ------------------------------------------------------------------
COPY clinical_bench/ /app/clinical_bench/

# ------------------------------------------------------------------
# Data files
# ------------------------------------------------------------------
# The three task datasets are bundled directly in the image so the
# environment works out of the box without any external downloads.
COPY clinical_bench/data/ /app/data/

# ------------------------------------------------------------------
# Environment variables
# ------------------------------------------------------------------
ENV DATA_PATH=/app/data
ENV MAX_STEPS=8
ENV PORT=8080
ENV PYTHONUNBUFFERED=1

# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# ------------------------------------------------------------------
# Start the server
# ------------------------------------------------------------------
EXPOSE 8080

CMD uvicorn clinical_bench.server.app:app \
    --host 0.0.0.0 \
    --port ${PORT} \
    --workers 1 \
    --timeout-keep-alive 75

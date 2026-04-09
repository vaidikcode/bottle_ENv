FROM node:22-slim AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/index.html frontend/vite.config.js ./
COPY frontend/src/ ./src/
RUN npm run build

FROM python:3.11-slim

# ------------------------------------------------------------------
# System packages
# ------------------------------------------------------------------
# libhts-dev pulls libcurl4-gnutls-dev; do not add libcurl4-openssl-dev
# because it conflicts on Debian trixie+.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        curl \
        libhts-dev \
        libbz2-dev \
        liblzma-dev && \
    rm -rf /var/lib/apt/lists/*

# ------------------------------------------------------------------
# Python dependencies
# ------------------------------------------------------------------
WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ------------------------------------------------------------------
# Application code + data
# ------------------------------------------------------------------
COPY server/ /app/server/
COPY client.py /app/client.py
COPY my_env_v4.py /app/my_env_v4.py
COPY data/ /app/data/
COPY openenv.yaml /app/openenv.yaml
COPY pyproject.toml /app/pyproject.toml
COPY inference.py /app/inference.py
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# ------------------------------------------------------------------
# Environment variables
# ------------------------------------------------------------------
ENV PYTHONPATH=/app
ENV DATA_PATH=/app/data
ENV MAX_STEPS=8
ENV PORT=8000
ENV PYTHONUNBUFFERED=1

# ------------------------------------------------------------------
# Health check
# ------------------------------------------------------------------
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# ------------------------------------------------------------------
# Start the server
# ------------------------------------------------------------------
EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn server.app:app --host 0.0.0.0 --port ${PORT} --workers 1 --timeout-keep-alive 75"]

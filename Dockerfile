# ==============================================================================
# Crew Media Ops — Backend Dockerfile (multi-stage)
# ==============================================================================

# --------------- Stage 1: Build dependencies ---------------
FROM python:3.12-slim AS builder

WORKDIR /build

# System deps required for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy only dependency files first (cache-friendly)
COPY pyproject.toml uv.lock ./

# Install production dependencies into a virtual env
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache -e ".[browser]"

# --------------- Stage 2: Production runtime ---------------
FROM python:3.12-slim AS runtime

WORKDIR /app

# Runtime system deps (libpq for PostgreSQL, curl for health checks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual env from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Copy application source
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY alembic.ini ./
COPY pyproject.toml ./

# Create directories for runtime data
RUN mkdir -p /app/data /app/logs /app/generated_images

# Non-root user for security
RUN groupadd --gid 1000 crew && \
    useradd --uid 1000 --gid crew --shell /bin/bash --create-home crew && \
    chown -R crew:crew /app
USER crew

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

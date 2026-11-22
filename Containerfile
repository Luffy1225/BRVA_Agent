# ==========================================================
# AeroAgent Podman Containerfile
# Compliant with Course Project Containerization Standards
# ==========================================================

FROM docker.io/library/python:3.11-slim

WORKDIR /app

# Install system utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code, scripts, data and tests
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY data/ ./data/
COPY tests/ ./tests/

# Security: Non-root user
RUN useradd -m -u 1000 aero && chown -R aero:aero /app
USER aero

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Default to interactive CLI (can be overridden by podman run arguments)
CMD ["python", "-m", "src.ui.cli"]

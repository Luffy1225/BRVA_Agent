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

# Expose Streamlit default port
EXPOSE 8501

# 預設啟動 Streamlit 視覺化網頁儀表板 (若需 CLI 模式可覆蓋指令: python -m src.ui.cli)
CMD ["python", "-m", "streamlit", "run", "src/ui/web.py", "--server.port=8501", "--server.address=0.0.0.0"]

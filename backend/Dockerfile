# ==========================================
# STAGE 1: Build dependencies in a venv
# ==========================================
FROM python:3.11-slim AS builder

WORKDIR /build

# Install compiler tools for any C-extension packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install virtualenv and build dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


# ==========================================
# STAGE 2: Lightweight runtime image
# ==========================================
FROM python:3.11-slim AS runner

WORKDIR /app

# Install ffmpeg for yt-dlp audio download capabilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create a non-root user for security
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -m -s /bin/bash appuser

# Copy application source code
COPY --chown=appuser:appgroup app/ ./app/

USER appuser

EXPOSE 8000

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# POS-MOBILE Backend Dockerfile
# Multi-stage build for smaller production image

# ---- Build Stage ----
FROM python:3.12-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ---- Production Stage ----
FROM python:3.12-slim

WORKDIR /app

# Create non-root user
RUN groupadd -r posuser && useradd -r -g posuser posuser

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /root/.local /home/posuser/.local

# Copy application code
COPY --chown=posuser:posuser . .

# Create data directory
RUN mkdir -p /data && chown -R posuser:posuser /data

# Switch to non-root user
USER posuser

# Add local packages to PATH
ENV PATH=/home/posuser/.local/bin:$PATH

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/sync/health || exit 1

# Run the application
CMD ["python", "run.py"]
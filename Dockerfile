# POS-MOBILE Backend — Dockerfile
FROM python:3.11-slim

WORKDIR /app

# ติดตั้ง dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY backend/ .

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()"

# Run (DEBUG=false เพื่อไม่ให้ reload ใน Docker)
ENV DEBUG=false
CMD ["python", "run.py"]

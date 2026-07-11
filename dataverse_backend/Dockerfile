FROM python:3.12-slim

WORKDIR /app

# curl is needed for the container health check
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements-mvp.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements-mvp.txt

# Copy application code
COPY . .

# Create runtime user and writable directories
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && mkdir -p /data /app/logs /app/plots /app/session_storage \
    && chown -R appuser:appuser /app /data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1

# Health check (PORT defaults to 7860, the Hugging Face Spaces convention)
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f "http://localhost:${PORT:-7860}/health/live" || exit 1

USER appuser

# Run application
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-7860}"]

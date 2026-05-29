FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create runtime user and writable directories
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && mkdir -p /data /app/logs /app/plots \
    && chown -R appuser:appuser /app /data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PATH="/app:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
    CMD curl -f http://localhost:8000/health/live || exit 1

USER appuser

# Run application
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
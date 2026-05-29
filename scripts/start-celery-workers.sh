#!/bin/bash
# Start Celery workers for DataVerse async tasks
# Usage: ./start-celery-workers.sh

set -e

echo "=========================================="
echo "DataVerse - Celery Worker Startup"
echo "=========================================="

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found"
    echo "Please copy .env.example to .env and configure it"
    exit 1
fi

# Load environment
export $(cat .env | grep -v '#' | xargs)

# Check if Redis is available
echo "Checking Redis connection..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "❌ Redis not available. Please start Redis first:"
    echo "   docker-compose up -d redis"
    exit 1
fi
echo "✓ Redis is available"

# Create logs directory
mkdir -p logs

# Start Celery workers
echo ""
echo "Starting Celery workers..."
echo "  - Fast queue (4 workers)"
echo "  - Slow queue (2 workers)"
echo ""

# Fast worker (for quick tasks: data validation, stats)
celery -A app.core.celery_config worker \
    --loglevel=info \
    --queues=fast \
    --concurrency=4 \
    --hostname=fast_worker@%h \
    --logfile=logs/celery_fast.log \
    --pidfile=logs/celery_fast.pid \
    &
FAST_PID=$!

# Slow worker (for long-running tasks: ML training, profiling)
celery -A app.core.celery_config worker \
    --loglevel=info \
    --queues=slow \
    --concurrency=2 \
    --hostname=slow_worker@%h \
    --logfile=logs/celery_slow.log \
    --pidfile=logs/celery_slow.pid \
    &
SLOW_PID=$!

echo "✓ Celery workers started"
echo "  Fast worker PID: $FAST_PID"
echo "  Slow worker PID: $SLOW_PID"
echo ""
echo "Press Ctrl+C to stop workers..."
echo ""

# Handle shutdown
trap "echo ''; echo 'Stopping workers...'; kill $FAST_PID $SLOW_PID 2>/dev/null; exit 0" INT TERM

# Wait for both workers
wait $FAST_PID $SLOW_PID

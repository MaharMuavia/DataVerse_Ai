# Start Celery workers for DataVerse async tasks
# Usage: .\start-celery-workers.ps1

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "DataVerse - Celery Worker Startup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "Error: .env file not found" -ForegroundColor Red
    Write-Host "Please copy .env.example to .env and configure it"
    exit 1
}

# Load environment from .env
$env_content = Get-Content ".env"
foreach ($line in $env_content) {
    if ($line -and -not $line.StartsWith("#")) {
        $key, $value = $line.Split("=", 2)
        if ($key -and $value) {
            [Environment]::SetEnvironmentVariable($key.Trim(), $value.Trim())
        }
    }
}

# Check if Redis is available
Write-Host "Checking Redis connection..." -ForegroundColor Cyan
try {
    $redis_check = & redis-cli ping 2>&1
    if ($redis_check -eq "PONG") {
        Write-Host "Redis is available" -ForegroundColor Green
    } else {
        throw "Redis not responding"
    }
} catch {
    Write-Host "Redis not available" -ForegroundColor Red
    Write-Host "Please start Redis first: docker-compose up -d redis"
    exit 1
}

# Create logs directory if it doesn't exist
if (-not (Test-Path "logs")) {
    New-Item -ItemType Directory -Path "logs" | Out-Null
}

Write-Host ""
Write-Host "Starting Celery workers..." -ForegroundColor Cyan
Write-Host "  - Fast queue (4 workers)" -ForegroundColor Gray
Write-Host "  - Slow queue (2 workers)" -ForegroundColor Gray
Write-Host ""

# Start fast worker in background
$fast_worker = Start-Process `
    -FilePath "python" `
    -ArgumentList "-m celery -A app.core.celery_config worker --queues=fast --concurrency=4 --hostname=fast_worker@%h --loglevel=info" `
    -WindowStyle Normal `
    -PassThru

# Start slow worker in background  
$slow_worker = Start-Process `
    -FilePath "python" `
    -ArgumentList "-m celery -A app.core.celery_config worker --queues=slow --concurrency=2 --hostname=slow_worker@%h --loglevel=info" `
    -WindowStyle Normal `
    -PassThru

Write-Host "Celery workers started" -ForegroundColor Green
Write-Host "  Fast worker PID: $($fast_worker.Id)" -ForegroundColor Gray
Write-Host "  Slow worker PID: $($slow_worker.Id)" -ForegroundColor Gray
Write-Host ""
Write-Host "Press Ctrl+C in the Windows to stop workers..." -ForegroundColor Yellow
Write-Host ""

# Wait for processes
Wait-Process -Id $fast_worker.Id, $slow_worker.Id

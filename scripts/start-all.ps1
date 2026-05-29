# Start DataVerse AI - Backend & Frontend

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  DataVerse AI - Full Stack Startup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Set working directory
$workDir = Split-Path -Parent -Path $PSScriptRoot
Set-Location $workDir

# Activate Python virtual environment
Write-Host "Activating Python environment..." -ForegroundColor Yellow
& "$workDir\.venv\Scripts\Activate.ps1"

# Start backend server in background
Write-Host "Starting backend server on port 8000..." -ForegroundColor Yellow
Write-Host "(This may take a few seconds...)" -ForegroundColor Gray
$backendProcess = Start-Process -PassThru -FilePath "python" -ArgumentList "scripts\\run_server.py" -WorkingDirectory $workDir -NoNewWindow

# Wait for backend to start
Write-Host "Waiting for backend to initialize..." -ForegroundColor Yellow
Start-Sleep -Seconds 4

# Check if backend is running
Write-Host "Checking backend health..." -ForegroundColor Yellow
$maxAttempts = 5
$attempt = 0
$backendReady = $false

while ($attempt -lt $maxAttempts -and -not $backendReady) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/docs" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            $backendReady = $true
            Write-Host "✓ Backend is running successfully!" -ForegroundColor Green
        }
    } catch {
        $attempt++
        if ($attempt -lt $maxAttempts) {
            Write-Host "  Waiting... (Attempt $attempt/$maxAttempts)" -ForegroundColor Yellow
            Start-Sleep -Seconds 2
        }
    }
}

if (-not $backendReady) {
    Write-Host "⚠ Backend may be slow to start, but continuing..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Starting frontend dev server on port 3000..." -ForegroundColor Yellow
Write-Host "(Frontend will open in your browser automatically)" -ForegroundColor Gray
Write-Host ""

# Navigate to frontend and start dev server
Push-Location "$workDir\dataverse_frontend"
npm run dev
Pop-Location


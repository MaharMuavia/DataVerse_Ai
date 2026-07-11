# Brings the DataVerse AI backend online for the live Vercel site.
# Prereqs (one-time): repo-root .venv with requirements-mvp.txt installed,
# ngrok installed + authtoken added, Supabase keys in dataverse_backend\.env.
#
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\start-live-backend.ps1 -NgrokDomain your-domain.ngrok-free.app

param(
    [Parameter(Mandatory = $true)]
    [string]$NgrokDomain
)

$repo = Split-Path $PSScriptRoot -Parent
$python = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { Write-Error "No .venv found at repo root"; exit 1 }

# 1. Start the backend in production mode (its own window; close it to stop)
$env:ENVIRONMENT = "production"
$env:CORS_ORIGINS = "https://data-verse-ai-liard.vercel.app,http://localhost:3000,http://127.0.0.1:3000"
$env:CORS_ORIGIN_REGEX = "^https://data-verse-[a-z0-9]+-mahar-muavias-projects\.vercel\.app$"
Start-Process -FilePath $python `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
    -WorkingDirectory (Join-Path $repo "dataverse_backend")

# 2. Wait for the API to answer
$ok = $false
foreach ($i in 1..30) {
    Start-Sleep -Seconds 2
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/health/live" -UseBasicParsing -TimeoutSec 3
        if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch {}
}
if (-not $ok) { Write-Error "Backend did not become healthy"; exit 1 }
Write-Host "Backend healthy on http://localhost:8000"

# 3. Start the ngrok tunnel on the static domain (blocks; Ctrl+C to stop)
Write-Host "Starting tunnel: https://$NgrokDomain -> localhost:8000"
ngrok http 8000 --url "https://$NgrokDomain"

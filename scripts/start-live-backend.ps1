# Brings the DataVerse AI backend online for the live Vercel site
# (https://data-verse-ai-liard.vercel.app).
#
# Easiest: double-click scripts\start-live-backend.cmd
# Manual:  powershell -ExecutionPolicy Bypass -File scripts\start-live-backend.ps1
#
# Keep the ngrok window open - the live site works while it runs.
# Prereqs (one-time, already done): repo-root .venv with requirements-mvp.txt,
# ngrok installed + authtoken added, Supabase keys in dataverse_backend\.env.

param(
    [string]$NgrokDomain = "morbidity-hunchback-rectangle.ngrok-free.dev"
)

$repo = Split-Path $PSScriptRoot -Parent
$python = Join-Path $repo ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { Write-Error "No .venv found at repo root"; Read-Host "Press Enter to close"; exit 1 }

function Test-BackendHealthy {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:8000/health/live" -UseBasicParsing -TimeoutSec 3
        return ($r.StatusCode -eq 200)
    } catch { return $false }
}

# 1. Start the backend unless one is already serving on port 8000
if (Test-BackendHealthy) {
    Write-Host "Backend already running on http://localhost:8000 - reusing it."
} else {
    Write-Host "Starting backend..."
    $env:ENVIRONMENT = "production"
    $env:CORS_ORIGINS = "https://data-verse-ai-liard.vercel.app,http://localhost:3000,http://127.0.0.1:3000"
    $env:CORS_ORIGIN_REGEX = "^https://data-verse-[a-z0-9]+-mahar-muavias-projects\.vercel\.app$"
    # DeepAnalyze via local Ollama is the preferred reasoning engine; the
    # provider chain falls back to other keys / deterministic mode when the
    # model server is not running, so this can never break the demo.
    $env:LLM_PROVIDER = "deepanalyze"
    $env:DEEPANALYZE_LOCAL_BASE_URL = "http://localhost:11434/v1"
    $env:DEEPANALYZE_MODEL = "hf.co/mattritchey/DeepAnalyze-8B-Q4_K_M-GGUF"
    Start-Process -FilePath $python `
        -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000" `
        -WorkingDirectory (Join-Path $repo "dataverse_backend") -WindowStyle Minimized

    $ok = $false
    foreach ($i in 1..30) {
        Start-Sleep -Seconds 2
        if (Test-BackendHealthy) { $ok = $true; break }
    }
    if (-not $ok) { Write-Error "Backend did not become healthy"; Read-Host "Press Enter to close"; exit 1 }
    Write-Host "Backend healthy on http://localhost:8000"
}

# 2. Clear any stale ngrok agent, then start the tunnel (blocks; close window to stop)
Stop-Process -Name ngrok -Force -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "Starting tunnel: https://$NgrokDomain -> localhost:8000"
Write-Host "The live site works while this window stays open."
Write-Host ""
ngrok http 8000 --url "https://$NgrokDomain"

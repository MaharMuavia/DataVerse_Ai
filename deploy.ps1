# DataVerse AI - Production Deployment Script (Windows)
# Usage: .\deploy.ps1 -Environment dev
# or: .\deploy.ps1 -Environment prod
# or: .\deploy.ps1 -Environment stop

param(
    [Parameter(Mandatory=$false)]
    [ValidateSet("dev", "prod", "stop")]
    [string]$Environment = "dev"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent -Path $MyInvocation.MyCommand.Definition

Write-Host "🚀 DataVerse AI Deployment Script" -ForegroundColor Cyan
Write-Host "Mode: $Environment"
Write-Host "Root: $ProjectRoot"
Write-Host ""

switch ($Environment) {
    "dev" {
        Write-Host "📦 Development Deployment..." -ForegroundColor Yellow
        
        # Check Docker
        if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
            Write-Host "❌ Docker not found. Please install Docker Desktop." -ForegroundColor Red
            exit 1
        }
        
        # Create .env if not exists
        if (-not (Test-Path "$ProjectRoot\.env")) {
            Write-Host "📝 Creating .env from template..." -ForegroundColor Yellow
            Copy-Item "$ProjectRoot\.env.example" "$ProjectRoot\.env"
            Write-Host "⚠️  Please edit .env with your API keys before deploying" -ForegroundColor Yellow
        }
        
        # Start services
        Write-Host "🔧 Starting services..." -ForegroundColor Yellow
        Set-Location $ProjectRoot
        & docker-compose up -d --build
        
        # Wait for postgres
        Write-Host "⏳ Waiting for PostgreSQL..." -ForegroundColor Yellow
        Start-Sleep -Seconds 5
        
        # Initialize database
        Write-Host "🗄️  Initializing database..." -ForegroundColor Yellow
        & docker-compose exec -T backend python -c "
from app.db.session_models import Base as SessionBase
from app.db.models import Base as LegacyBase
from app.db.base import engine
print('Creating tables...')
SessionBase.metadata.create_all(engine)
LegacyBase.metadata.create_all(engine)
print('✅ Database initialized')
"
        
        Write-Host ""
        Write-Host "✅ Deployment complete!" -ForegroundColor Green
        Write-Host ""
        Write-Host "📍 Access points:" -ForegroundColor Cyan
        Write-Host "  Frontend: http://localhost:3000"
        Write-Host "  Backend:  http://localhost:8001"
        Write-Host "  API Docs: http://localhost:8001/docs"
        Write-Host ""
        Write-Host "Commands:" -ForegroundColor Cyan
        Write-Host "  Logs:     docker-compose logs -f"
        Write-Host "  Stop:     docker-compose down"
    }
    
    "prod" {
        Write-Host "🏭 Production Deployment..." -ForegroundColor Yellow
        
        # Check .env exists
        if (-not (Test-Path "$ProjectRoot\.env")) {
            Write-Host "❌ .env file not found. Copy .env.example and configure it." -ForegroundColor Red
            exit 1
        }
        
        # Check for API key
        $envContent = Get-Content "$ProjectRoot\.env"
        if ($envContent -notmatch "OPENAI_API_KEY=sk-") {
            Write-Host "⚠️  Warning: OPENAI_API_KEY not configured in .env" -ForegroundColor Yellow
            $confirm = Read-Host "Continue anyway? (y/n)"
            if ($confirm -ne "y") {
                exit 1
            }
        }
        
        # Build and start
        Write-Host "🔧 Building production images..." -ForegroundColor Yellow
        Set-Location $ProjectRoot
        & docker-compose -f docker-compose.yml up -d --build
        
        # Health checks
        Write-Host "🏥 Running health checks..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        
        try {
            $null = Invoke-WebRequest -Uri http://localhost:8001/health -ErrorAction SilentlyContinue
        } catch {
            Write-Host "⚠️  Backend health check failed" -ForegroundColor Yellow
        }
        
        Write-Host ""
        Write-Host "✅ Production deployment complete!" -ForegroundColor Green
        Write-Host ""
        Write-Host "📍 Access: https://your-domain.com"
        Write-Host ""
        Write-Host "Next steps:" -ForegroundColor Cyan
        Write-Host "  1. Configure reverse proxy (nginx)"
        Write-Host "  2. Enable HTTPS with Let's Encrypt"
        Write-Host "  3. Set up monitoring"
        Write-Host "  4. Configure backups"
    }
    
    "stop" {
        Write-Host "🛑 Stopping services..." -ForegroundColor Yellow
        Set-Location $ProjectRoot
        & docker-compose down
        Write-Host "✅ Services stopped" -ForegroundColor Green
    }
}

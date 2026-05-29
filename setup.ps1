# Setup script for DataVerse development environment (Windows)
# This script initializes the local development environment with all dependencies

Write-Host "====================================================================================" -ForegroundColor Cyan
Write-Host "DataVerse - Development Environment Setup (Windows)" -ForegroundColor Cyan
Write-Host "====================================================================================" -ForegroundColor Cyan

# Check prerequisites
Write-Host "`nChecking prerequisites..." -ForegroundColor Blue

# Check Docker
try {
    docker --version > $null 2>&1
    Write-Host "✓ Docker found" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker is not installed" -ForegroundColor Red
    Write-Host "Please install Docker: https://docs.docker.com/desktop/" -ForegroundColor Red
    exit 1
}

# Check Docker Compose
try {
    docker-compose --version > $null 2>&1
    Write-Host "✓ Docker Compose found" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker Compose is not installed" -ForegroundColor Red
    exit 1
}

# Setup environment file
Write-Host "`nSetting up environment variables..." -ForegroundColor Blue
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "✓ Created .env from template" -ForegroundColor Green
    Write-Host "  Remember to update .env with your API keys!" -ForegroundColor Blue
} else {
    Write-Host "✓ .env already exists" -ForegroundColor Green
}

# Create directories
Write-Host "`nCreating required directories..." -ForegroundColor Blue
@("logs", "data", "tmp_report_exports", "plots") | ForEach-Object {
    New-Item -ItemType Directory -Force -Path $_ | Out-Null
}
Write-Host "✓ Directories created" -ForegroundColor Green

# Build and start services
Write-Host "`nBuilding and starting Docker services..." -ForegroundColor Blue
Write-Host "This may take a few minutes on first run..." -ForegroundColor Yellow

docker-compose down -v 2> $null
docker-compose build --no-cache
docker-compose up -d

# Wait for services to be healthy
Write-Host "`nWaiting for services to be ready..." -ForegroundColor Blue
$maxWait = 60
$waited = 0

while ($waited -lt $maxWait) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 2 -UseBasicParsing
        if ($response.StatusCode -eq 200) {
            Write-Host "✓ Backend is ready" -ForegroundColor Green
            break
        }
    } catch {
        $waited += 2
        Write-Host "Waiting for backend... ($waited/$maxWait)"
        Start-Sleep -Seconds 2
    }
}

# Display startup info
Write-Host "`n====================================================================================" -ForegroundColor Green
Write-Host "✓ Setup Complete!" -ForegroundColor Green
Write-Host "====================================================================================" -ForegroundColor Green

Write-Host "`nService URLs:" -ForegroundColor Blue
Write-Host "  Backend API:        http://localhost:8000/api"
Write-Host "  API Documentation:  http://localhost:8000/docs"
Write-Host "  Frontend:           http://localhost:3000"
Write-Host "  Redis:              localhost:6379"
Write-Host "  PostgreSQL:         localhost:5432"
Write-Host "  MinIO Console:      http://localhost:9001 (optional)"

Write-Host "`nDefault Credentials:" -ForegroundColor Blue
Write-Host "  Username: admin"
Write-Host "  Password: secret"

Write-Host "`nQuick Commands:" -ForegroundColor Blue
Write-Host "  View logs:          docker-compose logs -f backend"
Write-Host "  Stop services:      docker-compose down"
Write-Host "  Rebuild backend:    docker-compose up -d --build backend"

Write-Host "`nNext Steps:" -ForegroundColor Blue
Write-Host "  1. Open http://localhost:3000 in your browser"
Write-Host "  2. Login with admin/secret"
Write-Host "  3. Create a workspace and upload a dataset"
Write-Host "  4. Start analyzing with AI agents!"

Write-Host "`nDocumentation:" -ForegroundColor Blue
Write-Host "  See QUICKSTART.md for detailed setup instructions"
Write-Host "  See docs/ folder for architecture and API documentation"

Write-Host "`nHappy coding! 🚀`n" -ForegroundColor Green

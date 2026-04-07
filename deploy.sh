#!/bin/bash

# DataVerse AI - Production Deployment Script
# Usage: ./deploy.sh [dev|prod|stop]

set -e

ENV=${1:-dev}
PROJECT_ROOT=$(dirname "$(readlink -f "$0")")

echo "🚀 DataVerse AI Deployment Script"
echo "Mode: $ENV"
echo "Root: $PROJECT_ROOT"

case $ENV in
  dev)
    echo "📦 Development Deployment..."
    
    # Check if Docker is installed
    if ! command -v docker &> /dev/null; then
      echo "❌ Docker not found. Please install Docker."
      exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
      echo "❌ Docker Compose not found. Please install Docker Compose."
      exit 1
    fi
    
    # Create .env if not exists
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
      echo "📝 Creating .env from template..."
      cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
      echo "⚠️  Please edit .env with your API keys before deploying"
    fi
    
    # Start services
    echo "🔧 Starting services..."
    cd "$PROJECT_ROOT"
    docker-compose up -d --build
    
    # Wait for postgres
    echo "⏳ Waiting for PostgreSQL..."
    sleep 5
    
    # Initialize database
    echo "🗄️  Initializing database..."
    docker-compose exec -T backend python -c "
from app.db.session_models import Base as SessionBase
from app.db.models import Base as LegacyBase
from app.db.base import engine
print('Creating tables...')
SessionBase.metadata.create_all(engine)
LegacyBase.metadata.create_all(engine)
print('✅ Database initialized')
"
    
    echo ""
    echo "✅ Deployment complete!"
    echo ""
    echo "📍 Access points:"
    echo "  Frontend: http://localhost:3000"
    echo "  Backend:  http://localhost:8001"
    echo "  API Docs: http://localhost:8001/docs"
    echo ""
    echo "Logs: docker-compose logs -f"
    echo "Stop: docker-compose down"
    ;;
    
  prod)
    echo "🏭 Production Deployment..."
    
    # Check required files
    if [ ! -f "$PROJECT_ROOT/.env" ]; then
      echo "❌ .env file not found. Copy .env.example and configure it."
      exit 1
    fi
    
    # Validate .env has required keys
    if ! grep -q "OPENAI_API_KEY=sk-" "$PROJECT_ROOT/.env"; then
      echo "⚠️  Warning: OPENAI_API_KEY not configured in .env"
      read -p "Continue anyway? (y/n) " -n 1 -r
      echo
      if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
      fi
    fi
    
    # Build and start
    echo "🔧 Building production images..."
    cd "$PROJECT_ROOT"
    docker-compose -f docker-compose.yml up -d --build
    
    # Health checks
    echo "🏥 Running health checks..."
    sleep 10
    
    if ! curl -s http://localhost:8001/health > /dev/null; then
      echo "⚠️  Backend health check failed"
    fi
    
    echo ""
    echo "✅ Production deployment complete!"
    echo ""
    echo "📍 Access: https://your-domain.com"
    echo ""
    echo "Next steps:"
    echo "  1. Configure reverse proxy (nginx)"
    echo "  2. Enable HTTPS with Let's Encrypt"
    echo "  3. Set up monitoring"
    echo "  4. Configure backups"
    ;;
    
  stop)
    echo "🛑 Stopping services..."
    cd "$PROJECT_ROOT"
    docker-compose down
    echo "✅ Services stopped"
    ;;
    
  *)
    echo "Usage: $0 [dev|prod|stop]"
    echo ""
    echo "Examples:"
    echo "  $0 dev    - Start development environment"
    echo "  $0 prod   - Start production environment"
    echo "  $0 stop   - Stop all services"
    exit 1
    ;;
esac
#!/bin/bash

# Setup script for DataVerse development environment
# This script initializes the local development environment with all dependencies

set -e

echo "==============================================================================" 
echo "DataVerse - Development Environment Setup"
echo "================================================================================"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check prerequisites
echo -e "\n${BLUE}Checking prerequisites...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}✗ Docker is not installed${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
echo -e "${GREEN}✓ Docker found${NC}"

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}✗ Docker Compose is not installed${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi
echo -e "${GREEN}✓ Docker Compose found${NC}"

# Setup environment file
echo -e "\n${BLUE}Setting up environment variables...${NC}"
if [ ! -f .env ]; then
    cp .env.example .env
    echo -e "${GREEN}✓ Created .env from template${NC}"
    echo -e "${BLUE}  Remember to update .env with your API keys!${NC}"
else
    echo -e "${GREEN}✓ .env already exists${NC}"
fi

# Create directories
echo -e "\n${BLUE}Creating required directories...${NC}"
mkdir -p logs data tmp_report_exports plots
echo -e "${GREEN}✓ Directories created${NC}"

# Build and start services
echo -e "\n${BLUE}Building and starting Docker services...${NC}"
echo "This may take a few minutes on first run..."

docker-compose down -v 2>/dev/null || true
docker-compose build --no-cache
docker-compose up -d

# Wait for services to be healthy
echo -e "\n${BLUE}Waiting for services to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:8000/api/health > /dev/null; then
        echo -e "${GREEN}✓ Backend is ready${NC}"
        break
    fi
    echo "Waiting for backend... ($i/30)"
    sleep 2
done

# Check frontend
for i in {1..30}; do
    if curl -s http://localhost:3000 > /dev/null; then
        echo -e "${GREEN}✓ Frontend is ready${NC}"
        break
    fi
    echo "Waiting for frontend... ($i/30)"
    sleep 2
done

# Display startup info
echo -e "\n${GREEN}================================================================================${NC}"
echo -e "${GREEN}✓ Setup Complete!${NC}"
echo -e "${GREEN}================================================================================${NC}"

echo -e "\n${BLUE}Service URLs:${NC}"
echo "  Backend API:        http://localhost:8000/api"
echo "  API Documentation:  http://localhost:8000/docs"
echo "  Frontend:           http://localhost:3000"
echo "  Redis:              localhost:6379"
echo "  PostgreSQL:         localhost:5432"
echo "  MinIO Console:      http://localhost:9001 (optional)"

echo -e "\n${BLUE}Default Credentials:${NC}"
echo "  Username: admin"
echo "  Password: secret"

echo -e "\n${BLUE}Quick Commands:${NC}"
echo "  View logs:          docker-compose logs -f backend"
echo "  Stop services:      docker-compose down"
echo "  Rebuild backend:    docker-compose up -d --build backend"

echo -e "\n${BLUE}Next Steps:${NC}"
echo "  1. Open http://localhost:3000 in your browser"
echo "  2. Login with admin/secret"
echo "  3. Create a workspace and upload a dataset"
echo "  4. Start analyzing with AI agents!"

echo -e "\n${BLUE}Documentation:${NC}"
echo "  See QUICKSTART.md for detailed setup instructions"
echo "  See docs/ folder for architecture and API documentation"

echo -e "\n${GREEN}Happy coding! 🚀${NC}\n"

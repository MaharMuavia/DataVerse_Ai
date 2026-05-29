# 🚀 DataVerse - Production-Grade BI Platform

## Quick Start Guide

### Prerequisites
- Docker & Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)
- PostgreSQL 14+ (if not using Docker)
- Redis 7+ (if not using Docker)

---

## 🐳 Installation (Recommended: Docker)

### 1. Clone & Setup
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your configuration (API keys, database password, etc)
nano .env  # or your preferred editor
```

### 2. Start Services
```bash
# Start all services (PostgreSQL, Redis, Backend, Frontend, Workers)
docker-compose up -d

# Monitor logs
docker-compose logs -f backend

# Check health
curl http://localhost:8000/api/health
```

### 3. Access Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000/api
- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **MinIO Console** (optional): http://localhost:9001

---

## 💻 Local Development Setup

### Backend

```bash
# Navigate to backend
cd dataverse_backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL=postgresql+asyncpg://dataverse:dataverse_dev_password@localhost:5432/dataverse
export REDIS_URL=redis://localhost:6379/0
export SECRET_KEY=dev-secret-key
export ENVIRONMENT=development

# Run migrations (automatic on startup)
python -m uvicorn app.main:app --reload --port 8000

# In another terminal, start Celery worker
celery -A tasks.celery_app worker --loglevel=info
```

### Frontend

```bash
# Navigate to frontend
cd dataverse_frontend

# Install dependencies
npm install

# Set environment variables
export NEXT_PUBLIC_API_URL=http://localhost:8000/api
export NEXT_PUBLIC_WS_URL=ws://localhost:8000

# Start dev server
npm run dev  # runs on http://localhost:3000
```

---

## 🗄️ Database Setup

### Automatic (Recommended)
Database tables are created automatically on backend startup via migrations in `001_full_schema.sql`.

### Manual
```bash
# Connect to PostgreSQL
psql -U dataverse -d dataverse -h localhost

# Run migration manually
\i dataverse_backend/app/db/migrations/001_full_schema.sql

# Verify tables
\dt  # list tables
```

---

## 👤 Initial User Setup

### Demo Account (Pre-configured)
- **Username**: `admin`
- **Password**: `secret`

### Create New User
```bash
# Via REST API
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "user@example.com",
    "full_name": "New User",
    "password": "securepassword"
  }'
```

---

## 🔧 Configuration

### Environment Variables
See `.env.example` for all available options. Key variables:

```
DATABASE_URL                 # PostgreSQL connection string
REDIS_URL                    # Redis connection string
SECRET_KEY                   # JWT signing key (must change in production)
ANTHROPIC_API_KEY            # Claude API key
OPENAI_API_KEY              # OpenAI API key (fallback)
MAX_UPLOAD_SIZE_MB          # Max dataset file size (default: 100MB)
```

---

## 📚 API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - User login
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/refresh` - Refresh JWT token

### Workspaces
- `POST /api/workspaces/` - Create workspace
- `GET /api/workspaces/` - List user's workspaces
- `GET /api/workspaces/{id}` - Get workspace details

### Datasets
- `POST /api/workspaces/{id}/datasets/upload` - Upload file
- `GET /api/workspaces/{id}/datasets` - List datasets
- `GET /api/workspaces/{id}/datasets/{id}/preview` - Preview data

### Conversations
- `POST /api/workspaces/{id}/conversations` - Create chat
- `GET /api/workspaces/{id}/conversations` - List chats
- `POST /api/workspaces/{id}/conversations/{id}/messages` - Send message (SSE streaming)

---

## 🧪 Testing

### Backend
```bash
cd dataverse_backend
pytest tests/ -v
```

### Frontend
```bash
cd dataverse_frontend
npm run build  # Check for build errors
```

---

## 🐛 Troubleshooting

### Backend won't start
```bash
# Check database connection
docker-compose logs postgres

# Test connection
psql -U dataverse -d dataverse -h localhost -c "SELECT 1;"

# Rebuild without cache
docker-compose up -d --build backend
```

### Frontend can't connect to API
- Verify backend is running: `curl http://localhost:8000/api/health`
- Check `NEXT_PUBLIC_API_URL` in `.env.local`
- Check CORS settings in `backend/app/main.py`

### Celery worker not processing tasks
```bash
# Check Redis connection
redis-cli ping  # should return PONG

# Monitor Celery
celery -A tasks.celery_app inspect active
```

---

## 📦 Deployment

### Docker Image
```bash
# Build backend image
docker build -t dataverse-backend ./dataverse_backend

# Build frontend image
docker build -t dataverse-frontend ./dataverse_frontend

# Push to registry
docker tag dataverse-backend my-registry/dataverse-backend:latest
docker push my-registry/dataverse-backend:latest
```

###  Production Checklist
- [ ] Change `SECRET_KEY` to random string
- [ ] Use strong database password
- [ ] Enable HTTPS/SSL
- [ ] Configure CORS for production domain
- [ ] Set `ENVIRONMENT=production`
- [ ] Use external PostgreSQL database
- [ ] Use managed Redis service (AWS ElastiCache, etc.)
- [ ] Enable database backups
- [ ] Set up monitoring and logging
- [ ] Configure API key rotation

### Recommended Deployment Platforms
- **Backend**: Railway, Fly.io, Render
- **Frontend**: Vercel, Netlify
- **Database**: AWS RDS, Supabase
- **Storage**: AWS S3, Google Cloud Storage
- **Monitoring**: Datadog, New Relic, Sentry

---

## 📖 Documentation

- [Architecture Overview](docs/README.md)
- [API Reference](docs/API.md)
- [Database Schema](docs/DATABASE.md)
- [Agent System](docs/AGENTS.md)

---

## 🤝 Contributing

1. Create a feature branch
2. Commit your changes
3. Submit a pull request
4. Ensure all tests pass

---

## 📄 License

© 2025 DataVerse. All rights reserved.

---

## 💬 Support

For issues and questions:
- GitHub Issues: [dataverse-issues]
- Email: support@dataverse.ai
- Slack: [dataverse-community]

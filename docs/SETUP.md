# DataVerse AI - Complete Setup Guide

This guide covers all aspects of setting up and running the DataVerse AI platform, from local development to production deployment.

## Quick Start (5 minutes)

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone/navigate to the project
cd /path/to/FINAL3

# 2. Create environment file
cp .env.example .env

# 3. Update .env with your API keys
nano .env  # Edit OPENAI_API_KEY, DB_PASSWORD, etc.

# 4. Start all services
docker-compose up -d

# 5. Initialize database (first time only)
docker-compose exec backend python -m app.tools.init_db

# 6. Access the application
# Frontend: http://localhost:3000
# API Docs: http://localhost:8001/docs
```

### Option 2: Manual Setup (Local Development)

#### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL 16+

#### Backend Setup

```bash
# Navigate to backend directory
cd dataverse_backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure database
export DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dataverse

# Run migrations
python -c "from app.main import app; from app.db.base import engine, Base; Base.metadata.create_all(engine)"

# Start backend
uvicorn app.main:app --reload --port 8001
```

#### Frontend Setup

```bash
# Navigate to frontend directory
cd dataverse_frontend

# Install dependencies
npm install

# Set environment variable
export NEXT_PUBLIC_API_URL=http://localhost:8001

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:3000`.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DataVerse AI Platform                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐         ┌──────────────────┐           │
│  │                  │         │                  │           │
│  │  Frontend (UI)   │◄──────►│  Backend (API)   │           │
│  │  Next.js 14      │         │  FastAPI         │           │
│  │  Port: 3000      │         │  Port: 8001      │           │
│  │                  │         │                  │           │
│  └──────────────────┘         └────────┬─────────┘           │
│                                        │                     │
│                                        │                     │
│                              ┌─────────▼─────────┐           │
│                              │   PostgreSQL 16   │           │
│                              │   Port: 5432      │           │
│                              │   Database: DB    │           │
│                              └───────────────────┘           │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Database
DB_PASSWORD=your_secure_password
DB_PORT=5432

# Backend
BACKEND_PORT=8001
LOG_LEVEL=INFO

# Frontend
FRONTEND_PORT=3000
NEXT_PUBLIC_API_URL=http://localhost:8001

# API Keys (required for functionality)
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=...  # Optional fallback

# Session management
SESSION_LIFETIME_HOURS=24
```

### Database Configuration

#### Local PostgreSQL
If running locally, create the database:

```bash
createuser dataverse -P  # Create user with password
createdb -O dataverse dataverse  # Create database
```

#### Docker PostgreSQL
The `docker-compose.yml` handles this automatically.

## Usage Guide

### 1. Upload a Dataset

1. Open http://localhost:3000
2. Click "Upload Dataset" or drag-and-drop a CSV file
3. Supported formats: `.csv`, `.xlsx`, `.xls`
4. Maximum file size: 50MB

### 2. Ask Questions

After uploading, type natural language questions:
- "What are the top 10 products by revenue?"
- "Show me sales trends over time"
- "Which customer segments have the highest churn?"

### 3. Interpret Results

The system provides:
- **Instant Analysis** - Real-time insight detection
- **Interactive Charts** - Plotly visualizations you can hover/zoom
- **AI Narration** - Human-readable summaries of findings

## API Reference

### Core Endpoints

#### Upload Dataset
```bash
POST /upload
Content-Type: multipart/form-data
Body: file=<csv_file>

Response:
{
  "id": "session-uuid",
  "dataset_filename": "sales.csv",
  "dataset_rows": 10000,
  "dataset_cols": 15,
  "created_at": "2024-03-24T10:00:00Z"
}
```

#### Process Query
```bash
POST /sessions/{session_id}/query
Content-Type: application/json
Body: {"query": "What are top products?"}

Response:
{
  "intent": "top_products",
  "confidence": 0.95,
  "result_json": {...},
  "narration": "The top 3 products are...",
  "chart_spec": {...},
  "execution_ms": 1234
}
```

#### Stream Results (Real-time)
```bash
GET /stream/{session_id}
Accept: text/event-stream

Events:
- intent: {intent: "top_products", confidence: 0.95}
- analysis: {result_json: {...}}
- visualization: {chart_spec: {...}}
- narration: {text: "Summary..."}
- complete: {}
```

#### Get Query History
```bash
GET /sessions/{session_id}/queries

Response: [
  {
    "id": "query-uuid",
    "query_text": "Top products?",
    "intent": "top_products",
    "confidence": 0.95,
    "narration": "...",
    "execution_ms": 1234
  }
]
```

## Troubleshooting

### Database Connection Issues

**Error**: `connection refused`

```bash
# Check if PostgreSQL is running
docker-compose ps

# Restart PostgreSQL
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

### Backend Won't Start

```bash
# Check logs
docker-compose logs backend

# Verify database is ready
docker-compose exec backend python -c "from app.db.base import engine; engine.connect()"

# Rebuild container
docker-compose build backend
```

### Frontend Can't Connect to Backend

```bash
# Verify backend is running
curl http://localhost:8001/health

# Check frontend logs
docker-compose logs frontend

# Verify API URL in environment
echo $NEXT_PUBLIC_API_URL
```

### CORS Errors

If getting CORS errors, the backend CORS is configured to allow `http://localhost:3000`. For production, update `dataverse_backend/app/main.py`:

```python
allow_origins=[
    "http://localhost:3000",
    "https://your-production-domain.com"
]
```

## Performance Tuning

### For Large Datasets (>100K rows)

1. **Increase SHAP sampling**: Edit `dataverse_backend/app/agents/xai_agent.py`
   ```python
   SHAP_SAMPLE_SIZE = 500  # Reduce from 1000
   ```

2. **Enable compression**: Edit `docker-compose.yml`
   ```yaml
   environment:
     COMPRESSION_ENABLED: "true"
   ```

3. **Increase worker processes**: Edit backend startup
   ```bash
   uvicorn app.main:app --workers 4
   ```

### Database Indexing

For frequently queried columns in CSV data, add indexes in queries table:

```sql
CREATE INDEX idx_queries_session_id ON queries(session_id);
CREATE INDEX idx_queries_created_at ON queries(created_at);
```

## Production Deployment

### 1. Set Secure Passwords

```bash
# Generate strong password
openssl rand -base64 32

# Update .env
echo "DB_PASSWORD=$(openssl rand -base64 32)" >> .env
```

### 2. Configure Reverse Proxy (nginx)

```nginx
upstream backend {
    server backend:8000;
}

upstream frontend {
    server frontend:3000;
}

server {
    listen 80;
    server_name your-domain.com;

    location /api/ {
        proxy_pass http://backend/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://frontend;
    }
}
```

### 3. Enable HTTPS

Use Let's Encrypt with Certbot:

```bash
certbot certonly --standalone -d your-domain.com
```

Update docker-compose to mount SSL certificates:

```yaml
volumes:
  - /etc/letsencrypt:/etc/letsencrypt:ro
```

### 4. Use Docker Secrets (Swarm Mode)

```bash
# Create secrets
echo "password" | docker secret create db_password -

# Update docker-compose
environment:
  DB_PASSWORD_FILE: /run/secrets/db_password
```

## Monitoring

### Health Checks

Check system health:

```bash
# Backend health
curl http://localhost:8001/health

# Database connection
docker-compose exec backend python -c "from app.db.base import engine; engine.connect(); print('OK')"

# Frontend
curl http://localhost:3000
```

### Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs backend
docker-compose logs postgres

# Last N lines
docker-compose logs --tail 50 backend
```

## Backup & Recovery

### Database Backup

```bash
# Full backup
docker-compose exec postgres pg_dump -U dataverse dataverse > backup.sql

# Restore
docker-compose exec -T postgres psql -U dataverse dataverse < backup.sql
```

### Data Volume Backup

```bash
# Backup sessions data
docker-compose exec backend tar czf /tmp/sessions_backup.tar.gz /data/sessions/

# Copy from container
docker cp dataverse-backend:/tmp/sessions_backup.tar.gz .
```

## Support & Contributing

For issues, questions, or contributions:
1. Check the [Backend docs](./services/backend/README.md)
2. Check the [Frontend docs](./services/frontend/README.md)
3. Review API documentation: http://localhost:8001/docs

## License

This project is part of the DataVerse AI platform.

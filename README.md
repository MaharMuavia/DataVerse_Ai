# DataVerse AI - AI-Powered Business Intelligence Platform

A production-ready platform for intelligent data analysis, combining FastAPI backend, Next.js frontend, and advanced AI agents.

## 🚀 Features

### Core Capabilities
- **Real-time Data Analysis** - Upload CSV files and ask natural language questions
- **Interactive Visualizations** - Plotly-based charts with full interactivity
- **AI-Powered Insights** - Automatic pattern detection and recommendations
- **Streaming Results** - See analysis progress in real-time
- **Session Persistence** - Data survives server restarts
- **Explainability** - SHAP/LIME feature importance analysis

### Technical Highlights
- **Modern Stack**: Next.js 14, FastAPI, PostgreSQL
- **Real-time Streaming**: Server-Sent Events for live updates
- **Background Processing**: Async AutoML training
- **Robust Architecture**: Persistent sessions, confidence scoring, fallback chains
- **Production Ready**: Docker Compose, health checks, error handling

## 📋 Quick Start

### 1. One-Command Setup (Docker)

```bash
# Clone and navigate to project
cd /path/to/FINAL3

# Copy environment template
cp .env.example .env

# Edit .env with your API keys
nano .env  # Add OPENAI_API_KEY, set DB_PASSWORD, etc.

# Start entire platform
docker-compose up -d

# Initialize database (first run only)
docker-compose exec backend python tools/init_db.py

# Access applications
# Frontend: http://localhost:3000
# API Docs: http://localhost:8001/docs
```

### 2. Manual Setup (Development)

See [SETUP.md](./SETUP.md) for detailed local development instructions.

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────┐
│           DataVerse AI Platform                       │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Frontend (Next.js)    Backend (FastAPI)            │
│  ├─ Chat Interface     ├─ Intent Router             │
│  ├─ Data Upload        ├─ Query Processors         │
│  ├─ Chart Renderer     ├─ 11 AI Agents             │
│  └─ Real-time Sync     ├─ Streaming Responses      │
│                        └─ Session Management       │
│                             │                       │
│                             ▼                       │
│                      PostgreSQL 16                  │
│                      ├─ Sessions                    │
│                      ├─ Queries                     │
│                      ├─ Analysis Results           │
│                      └─ ML Jobs                    │
│                                                      │
└──────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
FINAL3/
├── docker-compose.yml          # Complete platform orchestration
├── .env.example                # Environment template
├── SETUP.md                    # Comprehensive setup guide
├── README.md                   # This file
│
├── dataverse_backend/          # FastAPI backend
│   ├── app/
│   │   ├── main.py            # FastAPI app definition
│   │   ├── api/               # REST endpoints
│   │   ├── agents/            # 11 AI agents
│   │   ├── db/                # Database layer
│   │   ├── core/              # Intent router, narration
│   │   ├── orchestrator/       # Query orchestration
│   │   └── state/             # Persistent sessions
│   ├── requirements.txt         # Python dependencies
│   ├── Dockerfile              # Container definition
│   └── README.md               # Backend documentation
│
├── dataverse_frontend/         # Next.js 14 frontend
│   ├── app/                   # App Router pages
│   ├── components/            # React components
│   │   ├── ChatInterface      # Main interface
│   │   ├── DatasetUploader    # File upload
│   │   ├── ChartRenderer      # Plotly integration
│   │   └── MessageBubble      # Message display
│   ├── lib/                   # API integration
│   ├── store/                 # Zustand state
│   ├── types/                 # TypeScript definitions
│   ├── package.json           # Node dependencies
│   ├── Dockerfile             # Container definition
│   └── README.md              # Frontend documentation
│
└── retail-agent/              # Legacy Ollama agent (optional)
```

## 🛠️ Key Components

### Backend (FastAPI)
- **11 Specialized Agents**: EDA, Visualization, AutoML, SHAP, LIME, Deepanalyze, etc.
- **Intent Router**: Confident intent classification with rule-based overrides
- **Persistent Sessions**: PostgreSQL + Parquet file storage
- **Streaming API**: Real-time query processing via SSE
- **Narrator**: LLM-powered explanations

### Frontend (Next.js 14)
- **Drag-Drop Upload**: Intuitive dataset import
- **Real-time Chat**: Streaming message updates
- **Interactive Charts**: Zoom, pan, hover interactions
- **Session Management**: Zustand-based state
- **API Integration**: Type-safe backend communication

### Database (PostgreSQL)
- **Sessions Table**: Session metadata + Parquet paths
- **Queries Table**: User queries and results
- **ML Jobs Table**: Async AutoML job tracking
- **Legacy Tables**: Datasets, UserQueries, AnalysisResults

## 🔌 API Endpoints

### Session Management
```bash
POST /upload                           # Upload dataset → session UUID
GET /sessions/{session_id}             # Get session info
```

### Query Processing
```bash
POST /sessions/{session_id}/query      # Process query
GET /sessions/{session_id}/queries     # Get query history
GET /stream/{session_id}               # SSE streaming
```

### ML/AutoML
```bash
POST /sessions/{session_id}/automl     # Train models
GET /sessions/{session_id}/automl/{id} # Get job status
```

See http://localhost:8001/docs for interactive API documentation.

## ⚙️ Configuration

### Environment Variables

Create `.env` from `.env.example`:

```env
# Database
DB_PASSWORD=secure_password
DB_PORT=5432

# Backend
BACKEND_PORT=8001
LOG_LEVEL=INFO

# Frontend
FRONTEND_PORT=3000
NEXT_PUBLIC_API_URL=http://localhost:8001

# AI API Keys (required)
OPENAI_API_KEY=sk-...
DEEPSEEK_API_KEY=...  # Optional fallback

# Sessions
SESSION_LIFETIME_HOURS=24
```

## 🧪 Usage Examples

### Upload Dataset
```bash
curl -X POST -F "file=@data.csv" http://localhost:8001/upload
```

### Process Query
```bash
curl -X POST http://localhost:8001/sessions/{id}/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are top products?"}'
```

### Stream Results
```bash
curl -N http://localhost:8001/stream/{id}
```

## 📊 Performance

### Benchmarks
- **Small datasets** (<10K rows): <500ms response time
- **Medium datasets** (10K-100K rows): <2s response time
- **Large datasets** (100K+ rows): <5s response time (with SHAP sampling)

### Optimization Tips
See [SETUP.md](./SETUP.md) → "Performance Tuning"

## 🐳 Docker Deployment

### Quick Start
```bash
docker-compose up -d
```

### Scale Backend
```bash
docker-compose up -d --scale backend=3
```

### View Logs
```bash
docker-compose logs -f backend
docker-compose logs -f postgres
docker-compose logs -f frontend
```

### Stop Everything
```bash
docker-compose down
```

## 🔒 Security

- ✅ Environment variables for secrets (not hardcoded)
- ✅ Health checks for all services
- ✅ CORS configured for frontend origin
- ✅ File type/size validation on upload
- ✅ SQL injection prevention (SQLAlchemy ORM)
- ✅ Session expiration (24 hours default)

For production, see [SETUP.md](./SETUP.md) → "Production Deployment"

## 📖 Documentation

- **[SETUP.md](./SETUP.md)** - Complete setup, configuration, and deployment
- **[dataverse_backend/README.md](./dataverse_backend/README.md)** - Backend architecture
- **[dataverse_frontend/README.md](./dataverse_frontend/README.md)** - Frontend guide
- **[API Docs](http://localhost:8001/docs)** - Interactive Swagger documentation

## 🐛 Troubleshooting

### Docker Issues
```bash
# Container won't start?
docker-compose logs backend
docker-compose ps

# Database issues?
docker-compose restart postgres
```

### Backend Issues
```bash
# Import errors?
docker-compose exec backend python -m pytest tests/

# Check health
curl http://localhost:8001/health
```

### Frontend Issues
```bash
# Can't connect to backend?
echo $NEXT_PUBLIC_API_URL
curl http://localhost:8001/health

# Build issues?
docker-compose build frontend
```

See [SETUP.md](./SETUP.md) → "Troubleshooting" for detailed solutions.

## 🚀 Production Checklist

- [ ] Set strong `DB_PASSWORD` (use `openssl rand -base64 32`)
- [ ] Update `OPENAI_API_KEY` and any other API keys
- [ ] Configure reverse proxy (nginx/Apache)
- [ ] Enable HTTPS with Let's Encrypt
- [ ] Set `LOG_LEVEL=WARNING`
- [ ] Configure backups (database dumps)
- [ ] Set up monitoring/alerting
- [ ] Test disaster recovery
- [ ] Document deployment process

See [SETUP.md](./SETUP.md) → "Production Deployment"

## 🧑‍💻 Development

### Backend Development
```bash
cd dataverse_backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend Development
```bash
cd dataverse_frontend
npm install
npm run dev
```

### Adding a New Agent
See `dataverse_backend/app/agents/base_agent.py` for the template.

## 📊 Phases Completed

- ✅ **Phase 1**: Backend hardening (sessions, intent router, streaming, AutoML, charts, validation, narration)
- ✅ **Phase 2**: Next.js 14 frontend (chat interface, uploads, components, state management)
- ✅ **Phase 3**: Docker Compose setup (multi-container orchestration, health checks)
- ✅ **Phase 4**: Documentation & Production setup (SETUP.md, API reference, deployment guide)

## 📞 Support

For issues or questions:
1. Check [SETUP.md](./SETUP.md) troubleshooting section
2. Review API docs at http://localhost:8001/docs
3. Check service logs: `docker-compose logs -f`
4. Review component README files

## 📄 License

This project is part of the DataVerse AI platform.

---

**Ready to get started?** See [SETUP.md](./SETUP.md) for step-by-step instructions!
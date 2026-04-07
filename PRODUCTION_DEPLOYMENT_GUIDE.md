# Production Deployment Guide for Agentic LLM

## Quick Start: 5-Minute Deployment

### Prerequisites
- Python 3.9+
- Docker & Docker Compose (for production)
- Ollama running locally or remotely
- PostgreSQL 12+ (production only)
- Redis 6+ (production only)

### Local Development
```bash
# 1. Install dependencies
cd dataverse_backend
pip install -r requirements.txt

# 2. Start Ollama (in separate terminal)
ollama serve &
ollama pull deepanalyze-8b

# 3. Run server
uvicorn app.main:app --reload --port 8000

# 4. Test health
curl http://localhost:8000/health
```

## Docker Deployment

### Build Image
```bash
docker build -t dataverse-ai:latest -f dataverse_backend/Dockerfile .
docker tag dataverse-ai:latest your-registry/dataverse-ai:latest
docker push your-registry/dataverse-ai:latest
```

### Docker Compose (Multi-Service)
```yaml
version: '3.8'
services:
  api:
    image: dataverse-ai:latest
    ports:
      - "8000:8000"
    environment:
      - DEEPANALYZE_BASE_URL=http://ollama:11434
      - REDIS_URL=redis://redis:6379
      - DATABASE_URL=postgresql://postgres:password@postgres:5432/dataverse
    depends_on:
      - ollama
      - redis
      - postgres

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=dataverse
    volumes:
      - postgres_data:/var/lib/postgresql/data

  frontend:
    image: dataverse-frontend:latest
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://api:8000

volumes:
  ollama_data:
  redis_data:
  postgres_data:
```

## Kubernetes Deployment

### Prerequisites
- Kubectl configured
- Helm 3+
- Storage class configured

### Deployment YAML
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: dataverse-config
data:
  DEEPANALYZE_BASE_URL: "http://ollama:11434"
  REDIS_URL: "redis://redis:6379"
  LOG_LEVEL: "INFO"

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: dataverse-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: dataverse-api
  template:
    metadata:
      labels:
        app: dataverse-api
    spec:
      containers:
      - name: api
        image: your-registry/dataverse-ai:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: dataverse-config
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5

---
apiVersion: v1
kind: Service
metadata:
  name: dataverse-api
spec:
  selector:
    app: dataverse-api
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
  type: LoadBalancer
```

## Performance Tuning

### Memory Configuration
```python
# In app/core/config.py
CONVERSATION_MEMORY_SIZE = 100  # Max concurrent sessions
SESSION_TTL_HOURS = 2
MAX_AGENT_ITERATIONS = 8
AGENT_TIMEOUT_SECONDS = 60
```

### LLM Optimization
```python
# For faster responses, reduce token limits
LLM_MAX_TOKENS_PLAN = 256  # Smaller plans
LLM_MAX_TOKENS_SYNTHESIS = 512
LLM_TIMEOUT_SECONDS = 20  # Stricter timeout
```

### Database Optimization
```sql
-- Create indexes on frequently queried fields
CREATE INDEX idx_session_id ON sessions(session_id);
CREATE INDEX idx_user_id ON user_queries(user_id);
CREATE INDEX idx_dataset_id ON analysis_results(dataset_id);

-- Archive old sessions monthly
DELETE FROM sessions WHERE last_activity < NOW() - INTERVAL '30 days';
```

### Redis Optimization
```bash
# Monitor Redis memory usage
redis-cli INFO memory

# Set memory policy
CONFIG SET maxmemory-policy allkeys-lru

# Enable persistence
CONFIG SET save "900 1 300 10 60 10000"
```

## Monitoring & Observability

### Prometheus Metrics
```python
from prometheus_client import Counter, Histogram, Gauge

# Register metrics
query_counter = Counter('agent_queries_total', 'Total queries processed')
response_time = Histogram('agent_response_seconds', 'Query response time')
active_sessions = Gauge('active_sessions', 'Active session count')
tool_calls = Counter('tool_calls_total', 'Tool executions by name', ['tool_name'])
```

### Structured Logging
```json
{
  "timestamp": "2024-03-25T10:30:45Z",
  "level": "INFO",
  "service": "dataverse-ai",
  "session_id": "abc123",
  "event": "agent_plan_generated",
  "steps": 3,
  "duration_ms": 245,
  "tools": ["dataset_profile", "compute_statistics", "generate_narrative"]
}
```

### Health Checks
```bash
# API health
curl http://api:8000/health

# LLM availability
curl http://api:8000/health/llm

# Database connectivity
curl http://api:8000/health/db

# Cache status
curl http://api:8000/health/redis
```

## Security Hardening

### API Authentication
```python
# All endpoints require JWT token
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

### Rate Limiting
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/agent/query")
@limiter.limit("10/minute")
async def agent_query(...):
    pass
```

### Data Privacy
```python
# Encrypt sensitive data
from cryptography.fernet import Fernet

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")
cipher = Fernet(ENCRYPTION_KEY)
encrypted_data = cipher.encrypt(dataset.encode())
```

### Network Security
```yaml
# Kubernetes NetworkPolicy
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: dataverse-network-policy
spec:
  podSelector:
    matchLabels:
      app: dataverse-api
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
  egress:
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 5432  # Postgres
    - protocol: TCP
      port: 6379  # Redis
    - protocol: TCP
      port: 11434 # Ollama
```

## Backup & Recovery

### Database Backup
```bash
# Daily backup
0 2 * * * pg_dump postgresql://user:pass@db/dataverse | gzip > /backups/dataverse-$(date +\%Y\%m\%d).sql.gz

# Restore
gunzip -c /backups/dataverse-20240325.sql.gz | psql postgresql://user:pass@db/dataverse
```

### Redis Persistence
```conf
# redis.conf
# RDB snapshots
save 900 1      # Every 15 min if 1 key changed
save 300 10     # Every 5 min if 10 keys changed
save 60 10000   # Every 60 sec if 10000 keys changed

# AOF logging
appendonly yes
appendfsync everysec
```

### Session Backup Strategy
```python
# Backup active sessions daily
async def backup_sessions():
    all_sessions = memory.sessions.values()
    backup_data = [
        {
            "session_id": s.session_id,
            "timestamp": datetime.now(),
            "message_count": len(s.messages),
            "filters": s.active_filters,
            "dataset_schema": s.dataset_schema
        }
        for s in all_sessions
    ]
    await save_to_s3(backup_data, f"backups/sessions/{date_str}.json")
```

## Troubleshooting

### LLM Connection Issues
```python
# Check LLM availability
from app.llm.llm_client import LLMClient
client = LLMClient()
print(client.is_available())  # Should return True

# Health check endpoint
GET /health/llm
```

### Memory Leaks
```python
# Monitor memory usage
import psutil
process = psutil.Process()
print(process.memory_info().rss / 1024 / 1024, "MB")

# Enable memory profiling
python -m memory_profiler app/main.py
```

### Query Timeout Issues
```python
# Increase timeout selectively
AGENT_TIMEOUT_SECONDS = {
    "train_classifier": 120,
    "explain_model_global": 60,
    "default": 30
}
```

## Cost Optimization

### LLM Usage Reduction
- Cache frequently asked queries
- Use smaller models for simple tasks
- Batch similar queries

### Storage Optimization
- Archive old analysis results after 90 days
- Compress dataset snapshots
- Use parquet instead of CSV

### Compute Optimization
- Use GPU for ML tools if available
- Parallelize tool execution
- Pre-compute common statistics

## Scaling Checklist

- [ ] Load test with 100+ concurrent users
- [ ] Set up auto-scaling based on memory/CPU
- [ ] Configure CDN for frontend assets
- [ ] Implement request queuing for peak loads
- [ ] Set up circuit breaker for LLM fallback
- [ ] Monitor and alert on key metrics
- [ ] Document runbooks for common issues
- [ ] Plan disaster recovery procedure
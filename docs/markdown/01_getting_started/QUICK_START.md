# DataVerse AI - Quick Reference

## 🚀 Quick Start (30 seconds)

```bash
cd FINAL3
cp .env.example .env
nano .env  # Add your OPENAI_API_KEY
docker-compose up -d
# Wait 10 seconds...
# Frontend: http://localhost:3000
# Backend:  http://localhost:8001
```

## 📋 Essential Commands

### Start/Stop
```bash
docker-compose up -d           # Start all services
docker-compose down            # Stop all services
docker-compose logs -f         # View all logs
docker-compose restart         # Restart all services
```

### Specific Services
```bash
docker-compose up -d postgres      # Start only database
docker-compose up -d backend       # Start only API
docker-compose up -d frontend      # Start only web UI

docker-compose logs backend        # Backend logs
docker-compose logs postgres       # Database logs
docker-compose logs frontend       # Frontend logs
```

### Database Operations
```bash
docker-compose exec postgres psql -U dataverse  # Connect to DB
docker-compose exec backend python -c "..."     # Run Python code
docker-compose exec postgres pg_dump -U dataverse dataverse > backup.sql  # Backup
docker-compose exec -T postgres psql -U dataverse dataverse < backup.sql  # Restore
```

### Rebuild
```bash
docker-compose build backend           # Rebuild backend image
docker-compose build frontend          # Rebuild frontend image
docker-compose build                   # Rebuild all images
docker-compose up -d --build          # Rebuild and start
```

## 📊 Monitoring

### Health Check
```bash
curl http://localhost:8001/health      # Backend health
curl http://localhost:3000             # Frontend health
docker-compose ps                      # Service status
```

### View Logs
```bash
docker-compose logs --tail 50 backend  # Last 50 lines
docker-compose logs -f backend         # Follow logs
docker-compose logs --timestamps       # With timestamps
```

## 🔧 Common Configurations

### Change Port Numbers
Edit `docker-compose.yml`:
```yaml
ports:
  - "8080:8000"  # Backend on 8080 instead of 8001
  - "3000:3000"  # Frontend stays on 3000
```

### Change Database Credentials
Edit `.env`:
```env
DB_PASSWORD=mynewpassword
DB_PORT=5433
```

### Change API Keys
Edit `.env`:
```env
OPENAI_API_KEY=sk-your-new-key
DEEPSEEK_API_KEY=new-key
```

## 🐛 Troubleshooting

### Backend won't start
```bash
docker-compose logs backend
docker-compose exec backend python -c "from app.main import app"
docker-compose restart backend
```

### Database connection error
```bash
docker-compose ps postgres
docker-compose logs postgres
docker-compose restart postgres
```

### Frontend can't reach backend
```bash
curl http://localhost:8001/health
docker-compose logs frontend
# Check NEXT_PUBLIC_API_URL in .env
```

### Out of disk space
```bash
docker system prune -a              # Remove unused images
docker volume prune                 # Remove unused volumes
docker container prune              # Remove stopped containers
```

## 🧹 Cleanup

### Remove everything
```bash
docker-compose down -v              # Stop and remove volumes
docker-compose rm -f                # Force remove containers
```

### Reset specific service
```bash
docker-compose down postgres        # Stop postgres
docker volume rm final3_postgres_data  # Delete data
docker-compose up -d postgres       # Restart fresh
```

## 📈 Performance Tuning

### Increase resources
Edit `docker-compose.yml`:
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

### Add more backend instances
```bash
docker-compose up -d --scale backend=3
```

## 🔐 Security

### Change database password
```bash
# Generate strong password
openssl rand -base64 32

# Update .env
echo "DB_PASSWORD=$(openssl rand -base64 32)" >> .env

# Restart with new password
docker-compose down
docker volume rm final3_postgres_data
docker-compose up -d
```

### Access database directly
```bash
docker-compose exec postgres psql -U dataverse
# Inside psql:
\l                    # List databases
\dt                   # List tables
SELECT * FROM sessions LIMIT 5;  # Query data
\q                    # Quit
```

## 📦 Deployment

### Development
```bash
./scripts/deploy.sh dev
# or (Windows):
.\scripts\deploy.ps1 -Environment dev
```

### Production
```bash
./scripts/deploy.sh prod
# or (Windows):
.\scripts\deploy.ps1 -Environment prod
```

### Stop Everything
```bash
./scripts/deploy.sh stop
# or (Windows):
.\scripts\deploy.ps1 -Environment stop
```

## 🧪 Testing

### Test API endpoint
```bash
# Upload file
curl -X POST -F "file=@data.csv" http://localhost:8001/upload

# Get API docs
curl http://localhost:8001/docs

# Backend health
curl http://localhost:8001/health
```

### Test database
```bash
docker-compose exec backend python -c "
from app.db.base import engine
from sqlalchemy import text
with engine.connect() as conn:
    result = conn.execute(text('SELECT 1'))
    print('✅ Database connected')
"
```

### Test frontend
```bash
curl http://localhost:3000
# Should return HTML page
```

## 📚 Full Documentation

- **Setup Instructions**: See [SETUP.md](SETUP_GUIDE.md)
- **Backend Details**: See [Backend docs](../03_implementation_and_services/BACKEND_SERVICE_GUIDE.md)
- **Frontend Details**: See [Frontend docs](../03_implementation_and_services/FRONTEND_SERVICE_GUIDE.md)
- **API Documentation**: http://localhost:8001/docs (when running)

## 💡 Pro Tips

1. **Keep logs handy**: `docker-compose logs -f &` in a separate terminal
2. **Use aliases**: `alias dc='docker-compose'`
3. **Check before restart**: `docker-compose ps` to see status
4. **Read errors carefully**: Most issues are in the logs
5. **Backup before major changes**: `pg_dump > backup.sql`

## 🆘 Get Help

1. Check logs: `docker-compose logs -f`
2. Read SETUP.md troubleshooting section
3. Verify all services running: `docker-compose ps`
4. Try restart: `docker-compose down && docker-compose up -d`
5. Check API docs: http://localhost:8001/docs

# 🧪 DataVerse - Testing & Validation Guide

This guide helps you verify that the DataVerse application is properly set up and working correctly.

---

## ✅ Pre-Flight Checklist

### System Requirements
- [ ] Docker installed (version 20.10+)
- [ ] Docker Compose installed (version 2.0+)
- [ ] Git installed
- [ ] 4GB RAM available
- [ ] 10GB disk space available
- [ ] Internet connection for downloading images

### Repository Setup
- [ ] Code cloned from repository
- [ ] `.env.example` exists
- [ ] `docker-compose.yml` exists
- [ ] `dataverse_backend/` directory exists
- [ ] `dataverse_frontend/` directory exists

---

## 🚀 Startup Validation

### Step 1: Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Verify .env was created
ls -la .env

# Check critical variables are set
grep DATABASE_URL .env
grep SECRET_KEY .env
```

✅ **Success**: `.env` file exists with critical variables

### Step 2: Start Services
```bash
# Option A: Linux/macOS
chmod +x setup.sh
./setup.sh

# Option B: Windows
.\setup.ps1

# Option C: Manual Docker
docker-compose down -v
docker-compose build
docker-compose up -d
```

✅ **Success**: All containers started without errors

### Step 3: Verify Services
```bash
# Check all containers are running
docker-compose ps

# Should show:
# NAME                              STATUS
# dataverse-postgres               Up (healthy)
# dataverse-redis                  Up (healthy)
# dataverse-backend                Up (healthy)
# dataverse-frontend               Up (healthy)
```

✅ **Success**: All 4 containers showing "Up"

---

## 🗄️ Database Validation

### Initialize Database
```bash
# Create admin user
docker-compose exec backend python app/db/seed_database.py

# Output should show:
# ✓ Database tables initialized
# ✓ Admin user created (username: admin, password: secret)
# ✓ Demo user created (username: demo, password: demo)
```

### Verify Database Connection
```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U dataverse -d dataverse -c "\dt"

# Should list tables:
#                    List of relations
# users                  | table | dataverse
# workspaces            | table | dataverse
# datasets              | table | dataverse
# conversations         | table | dataverse
# messages              | table | dataverse
# ml_jobs               | table | dataverse
# agent_logs            | table | dataverse
```

✅ **Success**: All 8 tables exist in database

### Check Demo Users
```bash
psql -U dataverse -d dataverse -c "SELECT username, email FROM users LIMIT 5;"

# Should show:
# username | email
# admin    | admin@dataverse.ai
# demo     | demo@dataverse.ai
```

✅ **Success**: Demo users created successfully

---

## 🔐 Backend API Validation

### Health Check
```bash
curl -s http://localhost:8000/api/health | jq .

# Should return:
# {"status":"ok","details":{"app":"DataVerse AI backend"}}
```

✅ **Success**: Backend is responding

### User Registration
```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "email": "test@example.com",
    "full_name": "Test User",
    "password": "testpass123"
  }' | jq .

# Should return user object with id, username, email
```

✅ **Success**: Registration endpoint works

### User Login
```bash
# Login with demo credentials
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=secret" | jq .

# Should return:
# {
#   "access_token": "eyJ0eXAi...",
#   "token_type": "bearer",
#   "expires_in": 1800
# }

# Save token for next requests
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -d "username=admin&password=secret" | jq -r '.access_token')

echo "Token saved: $TOKEN"
```

✅ **Success**: JWT token generated

### Get Current User
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/auth/me | jq .

# Should show current user info
```

✅ **Success**: Authentication working

### Create Workspace
```bash
curl -X POST http://localhost:8000/api/workspaces/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Workspace",
    "description": "For validation testing"
  }' | jq .

# Save workspace ID
WS_ID=$(curl -s -X POST http://localhost:8000/api/workspaces/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","description":"Test"}' | jq -r '.id')

echo "Workspace ID: $WS_ID"
```

✅ **Success**: Workspace created

### List Workspaces
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/workspaces/ | jq '.[] | {id, name}'
```

✅ **Success**: Workspace listed

---

## 📤 Dataset Upload Validation

### Create Sample CSV
```bash
cat > sample_data.csv << 'EOF'
product,sales,region,date
Widget A,1000,North,2025-01-01
Widget B,1500,South,2025-01-02
Widget C,2000,East,2025-01-03
Widget A,1200,West,2025-01-04
Widget B,1800,North,2025-01-05
EOF
```

### Upload Dataset
```bash
curl -X POST "http://localhost:8000/api/workspaces/$WS_ID/datasets/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample_data.csv" | jq .

# Save dataset ID
DATASET_ID=$(curl -s -X POST "http://localhost:8000/api/workspaces/$WS_ID/datasets/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample_data.csv" | jq -r '.id')

echo "Dataset ID: $DATASET_ID"
```

✅ **Success**: File uploaded

### List Datasets
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/workspaces/$WS_ID/datasets" | jq '.[] | {id, name, status}'

# Should show:
# {
#   "id": "uuid",
#   "name": "sample_data.csv",
#   "status": "profiling"
# }
```

✅ **Success**: Dataset listed

### Preview Dataset
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/workspaces/$WS_ID/datasets/$DATASET_ID/preview?rows=100" | jq '.columns'

# Should show: ["product", "sales", "region", "date"]
```

✅ **Success**: Data preview working

---

## 💬 Conversation Validation

### Create Conversation
```bash
curl -X POST "http://localhost:8000/api/workspaces/$WS_ID/conversations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"dataset_id\": \"$DATASET_ID\",
    \"title\": \"Sales Analysis\"
  }" | jq .

# Save conversation ID
CONV_ID=$(curl -s -X POST "http://localhost:8000/api/workspaces/$WS_ID/conversations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"dataset_id\":\"$DATASET_ID\",\"title\":\"Analysis\"}" | jq -r '.id')

echo "Conversation ID: $CONV_ID"
```

✅ **Success**: Conversation created

### List Conversations
```bash
curl -s -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/workspaces/$WS_ID/conversations" | jq '.[] | {id, title}'
```

✅ **Success**: Conversations listed

---

## 🌐 Frontend Validation

### Access Web UI
```bash
# Open browser
echo "Opening http://localhost:3000"
open http://localhost:3000  # macOS
# or
xdg-open http://localhost:3000  # Linux
# or
start http://localhost:3000  # Windows
```

### Test Login
1. Navigate to http://localhost:3000
2. Click login (or auto-redirected)
3. Enter credentials:
   - Username: `admin`
   - Password: `secret`
4. Click Login
5. Should redirect to dashboard

✅ **Success**: Login works

### Test Workspace Creation
1. Click "Create Workspace"
2. Enter name: "Browser Test"
3. Click Create
4. Should see workspace in list

✅ **Success**: Frontend workspace creation works

### Test Dataset Upload
1. Enter workspace
2. Click "Upload Dataset"
3. Drag and drop (or click to select) `sample_data.csv`
4. Wait for upload
5. Should see dataset in list with status "profiling"

✅ **Success**: File upload works in UI

---

## 📊 API Documentation

### View Swagger UI
```bash
open http://localhost:8000/docs
```

- Should show all endpoints
- Click endpoints to expand
- Try "Try it out" buttons

✅ **Success**: Swagger UI accessible

---

## 🔍 Logs & Debugging

### Backend Logs
```bash
docker-compose logs -f backend --tail 100

# Look for:
# - "Starting server process"
# - "Uvicorn running on http://0.0.0.0:8000"
# - No ERROR messages
```

### Database Logs
```bash
docker-compose logs postgres --tail 50

# Look for:
# - "database system is ready to accept connections"
# - No FATAL messages
```

### Frontend Logs
```bash
docker-compose logs frontend --tail 50

# Look for:
# - "Ready in Xs"
# - "▲ Next.js"
# - No build errors
```

---

## ⚠️ Common Issues & Solutions

### Issue: "Cannot connect to localhost:5432"
```bash
# Solution: Check PostgreSQL is running
docker-compose ps postgres

# If not running, start it
docker-compose up -d postgres

# Wait for health check
docker-compose exec postgres pg_isready -U dataverse
```

### Issue: "404 Not Found" on API endpoints
```bash
# Solution: Verify backend is running
curl http://localhost:8000/api/health

# Check logs
docker-compose logs backend | grep -i error
```

### Issue: "Connection refused" to frontend
```bash
# Solution: Check frontend is running
docker-compose ps frontend

# If not, check build logs
docker-compose logs frontend --tail 200

# Rebuild if needed
docker-compose down
docker-compose build frontend
docker-compose up -d frontend
```

### Issue: "Database does not exist"
```bash
# Solution: Run seed script
docker-compose exec backend python app/db/seed_database.py

# Or manually create tables
docker-compose exec backend python -c "
from app.db.models import Base
from app.db.base import get_engine
import asyncio
engine = get_engine()
asyncio.run(engine.run_sync(Base.metadata.create_all))
"
```

---

## 📝 Performance Testing

### Response Time Test
```bash
# Test API response time
time curl -s -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/auth/me > /dev/null

# Should complete in < 500ms
```

### Load Test (Basic)
```bash
# Install Apache Bench (if not installed)
# macOS: brew install httpd
# Linux: apt-get install apache2-utils

# Test endpoint under load
ab -n 100 -c 10 -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/workspaces/

# Shows average response time and throughput
```

---

## ✨ Full End-to-End Test

```bash
# 1. Setup
./setup.sh  # or setup.ps1 on Windows

# 2. Initialize database
docker-compose exec backend python app/db/seed_database.py

# 3. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -d "username=admin&password=secret" | jq -r '.access_token')

# 4. Create workspace
WS_ID=$(curl -s -X POST http://localhost:8000/api/workspaces/ \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"E2E Test"}' | jq -r '.id')

# 5. Upload dataset
DATASET_ID=$(curl -s -X POST "http://localhost:8000/api/workspaces/$WS_ID/datasets/upload" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample_data.csv" | jq -r '.id')

# 6. Create conversation
CONV_ID=$(curl -s -X POST "http://localhost:8000/api/workspaces/$WS_ID/conversations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"dataset_id\":\"$DATASET_ID\"}" | jq -r '.id')

# 7. Access frontend
echo "Test complete! Open http://localhost:3000 to verify"
```

---

## 🎉 Success Criteria

Your installation is **SUCCESSFUL** if:

- ✅ All 4 Docker containers are running
- ✅ `curl http://localhost:8000/api/health` returns 200
- ✅ Login returns JWT token
- ✅ Can create workspaces
- ✅ Can upload CSV files
- ✅ Can create conversations
- ✅ Frontend loads at http://localhost:3000
- ✅ Can login in UI and see dashboard
- ✅ No ERROR logs in containers

---

## 📞 Still Having Issues?

1. **Check documentation**: See `README.md` and `QUICKSTART.md`
2. **View logs**: `docker-compose logs -f backend`
3. **Restart services**: `docker-compose restart`
4. **Clean rebuild**: `docker-compose down -v && docker-compose up -d --build`
5. **Check .env**: Ensure all variables are set correctly

---

**Last Updated**: April 18, 2025
**Version**: 1.0

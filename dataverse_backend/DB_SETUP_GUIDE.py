"""Setup and Configuration Guide for PostgreSQL Database Integration

STEP 1: ENVIRONMENT CONFIGURATION
==================================
Create a .env file in the dataverse_backend directory with:

    DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dataverse_db
    
Replace 'user', 'password', and 'localhost' with your actual PostgreSQL credentials.

For local development with default PostgreSQL:
    DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/dataverse_db

For cloud PostgreSQL (e.g., AWS RDS, Railway, Heroku):
    DATABASE_URL=postgresql+asyncpg://user:password@host.region.rds.amazonaws.com:5432/dbname


STEP 2: INSTALL DEPENDENCIES
=============================
Run: pip install -r requirements.txt

This installs:
- sqlalchemy==2.0.23 (async ORM)
- asyncpg==0.29.0 (async PostgreSQL driver)
- psycopg2-binary==2.9.9 (sync fallback for migrations)


STEP 3: DATABASE CREATION
==========================
Create the PostgreSQL database manually or via script:

    createdb -U postgres dataverse_db

Or via psql:
    psql -U postgres
    CREATE DATABASE dataverse_db;


STEP 4: INITIALIZE DATABASE SCHEMA
===================================
Option A: Using SQLAlchemy ORM models directly in Python

    python -c "
from app.db.base import get_engine
from app.db.models import Base
import asyncio

async def init_db():
    engine = get_engine()
    if engine is None:
        raise RuntimeError('DATABASE_URL not configured')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('Database schema created successfully')

asyncio.run(init_db())
    "

Option B: Using Alembic for migrations (optional, future enhancement)
    - Install: pip install alembic
    - Initialize: alembic init migrations
    - Create migration: alembic revision --autogenerate -m "Initial schema"
    - Apply migration: alembic upgrade head


STEP 5: START THE APPLICATION
==============================
From the project root:

    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

The application will:
1. Test DB connectivity on startup
2. Log "Successfully connected to the database" if DATABASE_URL is configured
3. Gracefully continue if DB is unavailable (repositories will return None for db parameter)


DATABASE SCHEMA OVERVIEW
========================

Tables created by models.py:

1. datasets
   - id: UUID primary key
   - filename: dataset filename
   - row_count: number of rows
   - column_metadata: JSONB with column names and dtypes
   - uploaded_at: timestamp with timezone

2. user_queries
   - id: UUID primary key
   - dataset_id: FK to datasets.id
   - query_text: the user's query
   - parsed_intent: JSONB with OpenAI intent parsing result
   - created_at: timestamp with timezone

3. agent_runs
   - id: UUID primary key
   - dataset_id: FK to datasets.id
   - agent_name: name of the agent (IngestionAgent, EDAAgent, etc.)
   - action: action performed
   - reasoning: optional reasoning text
   - created_at: timestamp with timezone

4. analysis_results
   - id: UUID primary key
   - dataset_id: FK to datasets.id
   - computed_metrics: JSONB with analysis output
   - created_at: timestamp with timezone

5. reports
   - id: UUID primary key
   - analysis_result_id: FK to analysis_results.id
   - report_text: final report text or JSON
   - model_used: model name (OpenAI, DeepAnalyze, fallback, etc.)
   - created_at: timestamp with timezone


PERSISTENCE WORKFLOW
====================

1. Upload Dataset
   - /api/upload endpoint receives CSV
   - DataManager stores in-memory (session-based)
   - repositories.create_dataset() persists metadata to 'datasets' table
   - session_state["dataset_id"] = <uuid> for later reference

2. Submit Query
   - /api/query endpoint receives query text
   - repositories.log_user_query() persists query to 'user_queries' table
   - AgentOrchestrator.handle_query() is called with db session

3. Agent Execution
   - IngestionAgent.run() -> repositories.log_agent_run("IngestionAgent", ...)
   - EDAAgent.run() -> repositories.log_agent_run("EDAAgent", ...)
   - PreprocessingAgent.run() -> repositories.log_agent_run("PreprocessingAgent", ...)
   - All running in threadpool via run_in_threadpool()

4. Analysis
   - AnalysisAgent.run() -> repositories.save_analysis_result() persists computed metrics
   - DeepAnalyzeAgent.run() -> repositories.save_report() persists final report

5. Report Generation
   - Final report linked to analysis_result via analysis_result_id
   - model_used field documents which model generated the report


API ENDPOINT SIGNATURES
=======================

POST /api/upload
  Body: multipart file upload
  Returns: { session_id, message }
  Side Effects: creates Dataset record, sets session_state["dataset_id"]

POST /api/query
  Body: { session_id, query }
  Returns: { session_id, intent, computed_facts, report, action_required?, candidates? }
  Side Effects: creates UserQuery, AgentRun(s), AnalysisResult, Report records

POST /api/confirm_column
  Body: { session_id, column_name }
  Returns: { session_id, column_name, message }
  Side Effects: sets session_state["product_override"]

GET /api/health
  Returns: { status, details }
  No side effects


TESTING WITHOUT DATABASE
========================
If DATABASE_URL is not configured:
- Application starts normally
- db: AsyncSession = Depends(get_session) yields None
- All repositories are called with db=None and skip persistence
- System operates in "in-memory only" mode (suitable for development)


TROUBLESHOOTING
===============

Error: "FATAL: Ident authentication failed for user postgres"
-> Use password-based auth. Set DATABASE_URL with explicit password or ~/.pgpass file.

Error: "Cannot connect to PostgreSQL" during startup
-> Check DATABASE_URL format. Use postgresql+asyncpg:// for async.
-> Verify PostgreSQL is running: psql -U postgres -c "SELECT 1"

Error: "UndefinedTableError: relation 'datasets' does not exist"
-> Run Step 4 (database initialization) to create schema.

Error: "ImportError: No module named 'sqlalchemy'"
-> Run: pip install -r requirements.txt

Slow query performance on large datasets:
-> Add indexes: CREATE INDEX idx_datasets_uploaded_at ON datasets(uploaded_at);
-> Consider partitioning on created_at for audit tables.


PRODUCTION DEPLOYMENT
=====================
1. Use managed PostgreSQL (AWS RDS, Azure Database for PostgreSQL, etc.)
2. Set DATABASE_URL as environment variable (not in .env file)
3. Use connection pooling: pgbouncer or pgpool
4. Enable SSL: DATABASE_URL with ?sslmode=require
5. Implement automated backups
6. Monitor logs and performance via CloudWatch / Azure Monitor
7. Use Alembic for schema migrations (separate from application startup)
8. Set ENVIRONMENT=production in config for logging adjustments
"""

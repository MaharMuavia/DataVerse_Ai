# DataVerse AI Architecture

## Purpose

DataVerse AI is a SaaS-style AI data platform with:

- Next.js App Router frontend for authenticated user workflows
- FastAPI backend for auth, workspaces, datasets, conversations, billing, and AI catalog APIs
- PostgreSQL and Redis for persistence, caching, and async coordination
- Multi-provider AI model support for reasoning, intent parsing, and data-assistant workflows

## Top-Level Structure

```text
FINAL3/
|-- dataverse_frontend/        # Next.js application
|-- dataverse_backend/         # FastAPI backend
|-- docs/                      # Product, ops, and architecture docs
|-- docker-compose.yml         # Local development stack
|-- docker-compose.prod.yml    # Production-oriented compose stack
|-- .env.example               # Unified local environment template
```

## Frontend

```text
dataverse_frontend/
|-- app/
|   |-- auth/                  # Login and registration
|   |-- dashboard/             # SaaS summary screen
|   |-- billing/               # Subscription and Stripe readiness UI
|   |-- analytics/             # Analysis surfaces
|   |-- history/               # Session history UI
|   |-- settings/              # Product settings UI
|   |-- page.tsx               # Main assistant workspace
|-- components/                # Shell, sidebar, top bar, chat widgets
|-- lib/
|   |-- api-client.ts          # Authenticated API access
|   |-- auth-store.ts          # Zustand auth state
|   |-- protected-route.tsx    # Route guard
|-- store/                     # Local product state for assistant UX
|-- context/                   # Context bridge for store access
```

### Frontend flow

1. User authenticates through `/auth/login` or `/auth/register`
2. JWT is stored in a cookie and Zustand auth state
3. Protected pages use `ProtectedRoute`
4. React Query fetches dashboard, billing, and AI catalog data from FastAPI
5. Main assistant view handles uploads, chat state, and visual outputs

## Backend

```text
dataverse_backend/
|-- app/
|   |-- api/                   # FastAPI routers
|   |-- core/                  # Config, auth, middleware, logging, storage
|   |-- db/                    # SQLAlchemy models and session setup
|   |-- services/              # SaaS-oriented business logic
|   |-- workflow/              # Legacy and graph-driven analysis execution
|   |-- tasks/                 # Celery tasks
|   |-- main.py                # FastAPI app entrypoint
|-- config/                    # Multi-model provider router
|-- tests/                     # Backend test suite
```

### Backend API areas

- `/api/auth/*`: JWT registration, login, refresh, profile
- `/api/workspaces/*`: user-owned workspace management
- `/api/workspaces/{id}/datasets/*`: upload, metadata, preview
- `/api/workspaces/{id}/conversations/*`: threaded analysis and streaming responses
- `/api/dashboard/summary`: SaaS overview for the signed-in user
- `/api/billing/*`: plan catalog and Stripe-ready checkout flow
- `/api/ai/catalog`: model catalog and prompt profile guidance
- `/health/live` and `/health/ready`: runtime health endpoints

## Service Layer

The service layer keeps route files thin and easier to explain:

- `model_catalog.py`: supported providers, defaults, and task prompt profiles
- `billing_service.py`: plan catalog, Stripe readiness, checkout request assembly
- `dashboard_service.py`: workspace/dataset/conversation aggregation for the dashboard

This gives a cleaner separation than embedding product logic inside route handlers.

## Data Model

Core persistent entities:

- `users`
- `workspaces`
- `datasets`
- `conversations`
- `messages`
- `ml_jobs`
- `agent_logs`

Relationships:

- one user -> many workspaces
- one workspace -> many datasets
- one workspace -> many conversations
- one conversation -> many messages

## AI Model Strategy

Current product direction favors three primary providers:

- OpenAI for primary chat and fast intent parsing
- Anthropic for long-context analytical reasoning
- Mistral for open-model API coverage and lower-cost fallback

Additional fallback paths remain available through DeepSeek, Groq, and Ollama for local or cost-sensitive deployments.

## Deployment Shape

- Frontend: Vercel or any Next.js-compatible Node host
- Backend: Railway, Render, Fly.io, ECS, or a Docker host
- Database: PostgreSQL
- Cache/queue: Redis
- Storage: local for development, MinIO or S3 for production datasets

## Critical Runtime Flow

1. Authenticated user creates or selects a workspace
2. Dataset is uploaded and stored through the configured storage provider
3. Dataset metadata is persisted in PostgreSQL
4. User opens a conversation and sends a prompt
5. Workflow layer selects analysis path and AI provider
6. Results stream back as text, insights, or chart payloads
7. Conversation history is persisted for replay and auditability

## What Changed In This Stabilization Pass

- added a dedicated service layer for SaaS dashboard, billing, and model catalog logic
- added authenticated dashboard and billing pages in the frontend
- fixed login request encoding and workspace creation payload mismatch
- removed broken internal navigation targets and replaced them with valid product routes
- updated model defaults and provider catalog toward OpenAI, Anthropic, and Mistral
- added backend tests for SaaS service logic and HTTP route contracts

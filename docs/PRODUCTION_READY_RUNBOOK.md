# DataVerse Production Readiness Runbook

## 1. What is now production-hardened

- Backend request tracing via `X-Request-ID` and response timing headers.
- Security headers enabled by default for API responses.
- Env-driven CORS and trusted host controls.
- Liveness endpoint: `/health/live`
- Readiness endpoint: `/health/ready` (checks database and Redis)
- Backend container uses non-root runtime and Gunicorn + Uvicorn workers.
- Frontend uses Next.js standalone build output and non-root container runtime.
- Frontend response security headers and SWC minification enabled.
- CI workflow verifies backend syntax and frontend lint/build on pull requests.
- Dedicated production compose stack: `docker-compose.prod.yml`.

## 2. Pre-deploy checklist

- Set a strong `SECRET_KEY`.
- Set production `CORS_ORIGINS` and `TRUSTED_HOSTS`.
- Set `ENABLE_OPENAPI_DOCS=false`.
- Use managed PostgreSQL and Redis with backups.
- Configure HTTPS and reverse proxy (Nginx/Traefik/cloud load balancer).
- Ensure required model API keys are configured.

## 3. Deploy steps (Docker Compose)

1. Copy env template and fill production values:
   - `cp .env.example .env`
2. Build and start:
   - `docker compose -f docker-compose.prod.yml up -d --build`
3. Verify health:
   - `curl http://localhost:8000/health/live`
   - `curl http://localhost:8000/health/ready`
4. Verify frontend:
   - Open `http://localhost:3000`

## 4. Operational checks

- API readiness should return HTTP `200`.
- If readiness is degraded (`503`), inspect database and Redis connectivity.
- Watch backend logs for request IDs to trace failures end-to-end.

## 5. Recommended next hardening (phase 2)

- Add Redis-backed distributed rate limiting at API gateway level.
- Add Sentry/Datadog OpenTelemetry tracing.
- Add automatic DB migrations in deployment pipeline with rollback strategy.
- Add chaos/recovery tests and load testing with k6.
- Add secret management via cloud KMS/secret manager.

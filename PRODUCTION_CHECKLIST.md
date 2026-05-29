# 🚀 DataVerse Production Deployment Checklist

Use this checklist before deploying to production.

## ✅ Security

### Environment Variables
- [ ] Changed `SECRET_KEY` to a strong random string (min 32 characters)
- [ ] Set `ENVIRONMENT=production`
- [ ] Configured `DATABASE_URL` with production credentials
- [ ] Set strong `DB_PASSWORD` (not the default)
- [ ] Added LLM API keys (`ANTHROPIC_API_KEY` or `OPENAI_API_KEY`)
- [ ] Removed or secured all default credentials

### API Security
- [ ] Set `ENABLE_OPENAPI_DOCS=false` (hides /docs endpoint)
- [ ] Configured `CORS_ORIGINS` to only allow your frontend domain
- [ ] Set `TRUSTED_HOSTS` to your API domain only
- [ ] Enabled `HTTPS_REDIRECT=true` if using HTTPS
- [ ] Set `SECURE_HEADERS_ENABLED=true`
- [ ] Configured appropriate `RATE_LIMIT_REQUESTS` value

### SSL/TLS
- [ ] Obtained SSL certificate for domain
- [ ] Configured reverse proxy (Nginx/Caddy) with HTTPS
- [ ] Set up automatic certificate renewal (Let's Encrypt)
- [ ] Enabled HTTP → HTTPS redirect

## ✅ Database

### PostgreSQL Setup
- [ ] Created production database
- [ ] Set up database backups (automated daily)
- [ ] Configured connection pooling limits
- [ ] Enabled database logging for audit
- [ ] Set appropriate `max_connections` in PostgreSQL config
- [ ] Created database indexes (run migrations)

### Redis Setup
- [ ] Deployed Redis with persistence enabled
- [ ] Configured Redis password/ACL
- [ ] Set up Redis backup strategy
- [ ] Configured appropriate `maxmemory` limit

## ✅ Application

### Backend Configuration
- [ ] Set `LOG_LEVEL=INFO` or `WARNING` (not DEBUG)
- [ ] Enabled `LOG_JSON=true` for structured logging
- [ ] Configured `MAX_UPLOAD_SIZE_MB` appropriately
- [ ] Set up log rotation (for `LOG_DIR`)
- [ ] Configured `ACCESS_TOKEN_EXPIRE_MINUTES` per security policy
- [ ] Set appropriate Celery worker concurrency

### Frontend Configuration
- [ ] Set `NEXT_PUBLIC_API_URL` to production API URL
- [ ] Set `NEXT_PUBLIC_BACKEND_URL` correctly
- [ ] Configured `NEXT_PUBLIC_WS_URL` for WebSocket (wss://)
- [ ] Removed all development environment variables
- [ ] Built with `NODE_ENV=production`

## ✅ Monitoring & Observability

### Error Tracking
- [ ] Configured Sentry `SENTRY_DSN` (backend and frontend)
- [ ] Set appropriate `SENTRY_TRACES_SAMPLE_RATE` (0.1 recommended)
- [ ] Tested error reporting to Sentry

### Logging
- [ ] Centralized log collection configured (e.g., CloudWatch, DataDog)
- [ ] Set up log retention policy
- [ ] Configured alerts for critical errors

### Health Checks
- [ ] Verified `/health/live` endpoint returns 200
- [ ] Verified `/health/ready` checks DB and Redis
- [ ] Set up monitoring dashboard (Grafana/Prometheus)
- [ ] Configured uptime monitoring

## ✅ Infrastructure

### Docker Deployment
- [ ] Using production-ready Docker images (not development mounts)
- [ ] Configured resource limits (CPU, memory) for containers
- [ ] Set up container restart policies (`restart: always`)
- [ ] Configured Docker logging driver
- [ ] Using Docker secrets or external secret management

### Scalability
- [ ] Load balancer configured if running multiple instances
- [ ] Horizontal scaling tested for backend
- [ ] Celery workers scaled appropriately
- [ ] Database connection pooling configured
- [ ] Redis configured for high availability (Sentinel/Cluster if needed)

### Storage
- [ ] Configured persistent volumes for database
- [ ] Set up S3 or MinIO for file storage (`STORAGE_TYPE`)
- [ ] Configured backup strategy for uploaded datasets
- [ ] Set appropriate file retention policies

## ✅ Performance

### Backend
- [ ] Enabled Gunicorn with multiple workers (2-4x CPU cores)
- [ ] Configured uvicorn worker timeout appropriately
- [ ] Set up CDN for static assets (if applicable)
- [ ] Database query optimization verified
- [ ] Implemented caching strategy (Redis)

### Frontend
- [ ] Next.js built in production mode (`npm run build`)
- [ ] Static assets served from CDN
- [ ] Image optimization configured
- [ ] Bundle size analyzed and optimized

## ✅ Testing

### Pre-Deployment
- [ ] All unit tests passing
- [ ] Integration tests passing
- [ ] Load testing completed
- [ ] Security scan completed (OWASP ZAP, Snyk)
- [ ] Dependency vulnerabilities checked (`npm audit`, `pip check`)

### Post-Deployment
- [ ] Smoke tests passed in production
- [ ] Upload and analyze dataset workflow tested
- [ ] Chat and streaming responses working
- [ ] Authentication flow tested
- [ ] All agents responding correctly

## ✅ Compliance & Legal

### Data Privacy
- [ ] GDPR compliance reviewed (if applicable)
- [ ] Data retention policy documented
- [ ] User data export/deletion mechanism implemented
- [ ] Privacy policy updated
- [ ] Terms of service updated

### API Usage
- [ ] LLM API usage limits understood
- [ ] Cost monitoring configured for LLM APIs
- [ ] Fallback providers configured if primary fails

## ✅ Disaster Recovery

### Backups
- [ ] Database backup automated (daily)
- [ ] Redis backup strategy in place
- [ ] Application code in version control (Git)
- [ ] Backup restoration tested
- [ ] Documented recovery procedures (RTO/RPO defined)

### Rollback Plan
- [ ] Previous version tagged in Git
- [ ] Rollback procedure documented
- [ ] Database migration rollback tested
- [ ] Blue-green deployment or canary release strategy

## ✅ Documentation

### Operational
- [ ] Runbook created for common operations
- [ ] Incident response procedures documented
- [ ] On-call rotation defined
- [ ] Contact information for critical issues

### Technical
- [ ] API documentation up to date
- [ ] Architecture diagrams current
- [ ] Environment variables documented
- [ ] Deployment guide updated

## 🚨 Common Production Issues

### Issue: High Memory Usage
**Solution**: 
- Reduce Celery worker concurrency
- Optimize large dataset processing
- Enable dataset pagination

### Issue: Slow Response Times
**Solution**:
- Check database query performance
- Verify Redis connection
- Review LLM API latency
- Increase worker count

### Issue: Database Connection Errors
**Solution**:
- Increase connection pool size
- Check `max_connections` in PostgreSQL
- Verify network connectivity
- Review connection timeout settings

### Issue: LLM API Rate Limits
**Solution**:
- Implement exponential backoff
- Configure multiple API keys
- Enable fallback providers
- Add request queuing

---

## ✅ Final Pre-Launch Steps

1. **Dry Run**: Deploy to staging environment first
2. **Load Test**: Simulate expected production traffic
3. **Security Audit**: Third-party penetration testing
4. **Team Training**: Ensure operations team is trained
5. **Communication**: Notify stakeholders of launch window
6. **Monitoring**: Verify all alerts and dashboards working
7. **Rollback Plan**: Have rollback procedure ready
8. **Go Live**: Deploy during low-traffic window

---

**Remember**: Production deployment is a process, not a one-time event. Continuous monitoring and improvement are essential!

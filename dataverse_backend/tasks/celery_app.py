from celery import Celery
import os
from app.core.config import settings

# Celery is optional - use memory backend if Redis not configured
redis_url = getattr(settings, 'REDIS_URL', os.getenv('REDIS_URL', None))

celery_app = Celery("dataverse")
if redis_url:
    celery_app.config_from_object({
        "broker_url": redis_url,
        "result_backend": redis_url + "/1",
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "task_routes": {
            "tasks.eda_tasks.*": {"queue": "fast"},
            "tasks.ml_tasks.*": {"queue": "slow"},
            "tasks.xai_tasks.*": {"queue": "slow"},
        },
        "task_time_limit": 300,
        "task_soft_time_limit": 240,
        "worker_prefetch_multiplier": 1,
    })
else:
    # Fallback to memory broker
    celery_app.config_from_object({
        "broker_url": "memory://",
        "result_backend": "cache+memory://",
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
    })
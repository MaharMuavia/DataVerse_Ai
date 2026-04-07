from celery import Celery
from core.config import settings

celery_app = Celery("dataverse")
celery_app.config_from_object({
    "broker_url": settings.REDIS_URL,
    "result_backend": settings.REDIS_URL + "/1",
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
"""Celery configuration for async task processing.

Queues:
- default: General tasks
- fast: Quick operations (data validation, stats)
- slow: Long-running tasks (ML training, profiling)
"""
import logging

logger = logging.getLogger(__name__)

try:
    from celery import Celery
    from kombu import Exchange, Queue
    from .config import settings

    celery_app = Celery(
        "dataverse",
        broker=settings.CELERY_BROKER_URL,
        backend=settings.CELERY_RESULT_BACKEND,
    )

    celery_app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=30 * 60,
        task_soft_time_limit=25 * 60,
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=1000,
    )

    default_exchange = Exchange("celery", type="direct")
    celery_app.conf.task_queues = (
        Queue("default", exchange=default_exchange, routing_key="default"),
        Queue("fast", exchange=default_exchange, routing_key="fast"),
        Queue("slow", exchange=default_exchange, routing_key="slow"),
    )

    celery_app.conf.task_routes = {
        "tasks.data_validation.*": {"queue": "fast"},
        "tasks.compute_stats.*": {"queue": "fast"},
        "tasks.profile_dataset.*": {"queue": "slow"},
        "tasks.train_ml_model.*": {"queue": "slow"},
        "tasks.generate_insights.*": {"queue": "slow"},
    }

except Exception as exc:
    logger.warning("Celery not available (Redis may not be running): %s", exc)
    celery_app = None

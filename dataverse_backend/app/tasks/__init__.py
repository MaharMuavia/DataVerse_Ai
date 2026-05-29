"""Celery async tasks for background job processing.

Task modules:
- profile_tasks: Dataset profiling with Ydata
- ml_tasks: Machine learning with PyCaret
"""

from .profile_tasks import profile_dataset_task, compute_quick_stats
from .ml_tasks import (
    train_regression_model_task,
    train_classification_model_task,
    batch_predict_task,
)

__all__ = [
    "profile_dataset_task",
    "compute_quick_stats",
    "train_regression_model_task",
    "train_classification_model_task",
    "batch_predict_task",
]

# Celery configuration for HireLoop workers

from __future__ import absolute_import, unicode_literals
import os
from celery import Celery

# Load settings from environment via settings module (reuse Redis config)
from hireloop.apps.api.app.core.settings import settings

celery_app = Celery(
    "hireloop",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["hireloop.apps.api.app.workers.tasks"],
)

# Optional Celery configuration defaults
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_time_limit=300,  # seconds
)

# Autodiscover tasks from all registered apps (if any)
celery_app.autodiscover_tasks()

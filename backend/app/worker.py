from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery("uah", broker=settings.REDIS_URL, backend=settings.REDIS_URL, include=["app.tasks.job_sync"])
celery_app.conf.update(
    timezone="UTC",
    task_default_queue="uah_jobs",
    beat_schedule={
        "dispatch-scheduled-job-sweeps": {
            "task": "app.tasks.job_sync.dispatch_scheduled_sweeps",
            "schedule": max(int(settings.JOB_SYNC_DISPATCH_INTERVAL_SECONDS), 60),
        },
        "cleanup-stale-hidden-jobs": {
            "task": "app.tasks.job_sync.cleanup_cached_jobs",
            "schedule": max(int(settings.JOB_SYNC_CLEANUP_INTERVAL_SECONDS), 300),
        },
    },
)

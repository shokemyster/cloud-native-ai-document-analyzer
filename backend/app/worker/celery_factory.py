"""Celery application factory shared by publishers and workers."""

from celery import Celery

from app.config.settings import Settings, get_settings
from app.messaging.base import DOCUMENT_PROCESSING_TASK_NAME


def create_celery(settings: Settings | None = None) -> Celery:
    """Create a Celery application with production-oriented defaults."""

    resolved_settings = settings or get_settings()
    application = Celery(
        "ai_document_analyzer",
        broker=resolved_settings.redis_url,
        include=["app.worker.tasks"],
    )
    application.conf.update(
        accept_content=["json"],
        broker_connection_retry_on_startup=True,
        broker_connection_timeout=(
            resolved_settings.celery_broker_connection_timeout_seconds
        ),
        broker_transport_options={
            "socket_connect_timeout": (
                resolved_settings.celery_broker_connection_timeout_seconds
            ),
            "socket_timeout": (
                resolved_settings.celery_broker_connection_timeout_seconds
            ),
            "visibility_timeout": (resolved_settings.celery_visibility_timeout_seconds),
        },
        enable_utc=True,
        result_backend=None,
        task_acks_late=True,
        task_default_queue=resolved_settings.celery_queue_name,
        task_ignore_result=True,
        task_reject_on_worker_lost=True,
        task_routes={
            DOCUMENT_PROCESSING_TASK_NAME: {
                "queue": resolved_settings.celery_queue_name
            }
        },
        task_serializer="json",
        task_soft_time_limit=(resolved_settings.celery_task_soft_time_limit_seconds),
        task_time_limit=resolved_settings.celery_task_time_limit_seconds,
        timezone="UTC",
        worker_cancel_long_running_tasks_on_connection_loss=True,
        worker_prefetch_multiplier=1,
    )
    return application

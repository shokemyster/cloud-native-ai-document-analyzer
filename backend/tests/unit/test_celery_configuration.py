"""Unit tests for Celery configuration and task publishing."""

from pathlib import Path
from typing import Any, cast
from uuid import uuid4

import pytest
from celery import Celery

from app.config.settings import Settings
from app.messaging.base import DOCUMENT_PROCESSING_TASK_NAME
from app.messaging.celery_publisher import CeleryDocumentTaskPublisher
from app.worker.celery_factory import create_celery


class RecordingCelery:
    """Minimal Celery test double recording publication arguments."""

    def __init__(self) -> None:
        self.publication: dict[str, Any] | None = None
        self.closed = False

    def send_task(
        self,
        name: str,
        *,
        args: list[str],
        task_id: str,
        queue: str,
    ) -> None:
        self.publication = {
            "name": name,
            "args": args,
            "task_id": task_id,
            "queue": queue,
        }

    def close(self) -> None:
        self.closed = True


def build_settings(tmp_path: Path) -> Settings:
    return Settings.model_validate(
        {
            "database_url": "postgresql+asyncpg://unused",
            "upload_directory": tmp_path,
            "redis_url": "redis://redis:6379/0",
        }
    )


def test_celery_uses_safe_queue_defaults(tmp_path: Path) -> None:
    application = create_celery(build_settings(tmp_path))

    assert application.conf.accept_content == ["json"]
    assert application.conf.result_backend is None
    assert application.conf.task_acks_late is True
    assert application.conf.task_ignore_result is True
    assert application.conf.task_reject_on_worker_lost is True
    assert application.conf.worker_prefetch_multiplier == 1
    assert application.conf.task_default_queue == "documents"


@pytest.mark.asyncio
async def test_publisher_sends_only_job_identity() -> None:
    celery = RecordingCelery()
    publisher = CeleryDocumentTaskPublisher(
        cast(Celery, celery),
        queue_name="documents",
    )
    job_id = uuid4()

    await publisher.publish(job_id)
    await publisher.close()

    assert celery.publication == {
        "name": DOCUMENT_PROCESSING_TASK_NAME,
        "args": [str(job_id)],
        "task_id": str(job_id),
        "queue": "documents",
    }
    assert celery.closed is True

"""Celery implementation of the processing-job publisher."""

import asyncio
from uuid import UUID

from celery import Celery

from app.messaging.base import DOCUMENT_PROCESSING_TASK_NAME, TaskPublishError


class CeleryDocumentTaskPublisher:
    """Publish document-processing tasks through a Celery broker."""

    def __init__(self, celery: Celery, *, queue_name: str) -> None:
        self._celery = celery
        self._queue_name = queue_name

    async def publish(self, job_id: UUID) -> None:
        try:
            await asyncio.to_thread(
                self._celery.send_task,
                DOCUMENT_PROCESSING_TASK_NAME,
                args=[str(job_id)],
                task_id=str(job_id),
                queue=self._queue_name,
            )
        except Exception as exc:
            raise TaskPublishError("Failed to publish processing job") from exc

    async def close(self) -> None:
        await asyncio.to_thread(self._celery.close)

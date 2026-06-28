"""Application-facing background-task publishing contract."""

from typing import Protocol
from uuid import UUID

DOCUMENT_PROCESSING_TASK_NAME = "documents.process"


class TaskPublishError(Exception):
    """Raised when a processing job cannot be submitted to the broker."""


class DocumentTaskPublisher(Protocol):
    """Publish document-processing jobs without exposing broker details."""

    async def publish(self, job_id: UUID) -> None: ...

    async def close(self) -> None: ...

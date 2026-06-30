"""FastAPI dependency wiring for infrastructure and services."""

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.database.session import Database
from app.messaging.base import DocumentTaskPublisher
from app.repositories.document_analyses import DocumentAnalysisRepository
from app.repositories.documents import DocumentRepository
from app.repositories.processing_jobs import ProcessingJobRepository
from app.services.analyses import DocumentAnalysisService
from app.services.documents import DocumentService
from app.services.jobs import ProcessingJobService
from app.storage.base import ObjectStorage


def get_database(request: Request) -> Database:
    """Return the database manager initialized during application startup."""

    return cast(Database, request.app.state.database)


async def get_session(
    database: Annotated[Database, Depends(get_database)],
) -> AsyncIterator[AsyncSession]:
    """Provide one database session for the current request."""

    async with database.session() as session:
        yield session


def get_storage(request: Request) -> ObjectStorage:
    """Return the configured object-storage adapter."""

    return cast(ObjectStorage, request.app.state.storage)


def get_redis(request: Request) -> Redis:
    """Return the async Redis client used for readiness checks."""

    return cast(Redis, request.app.state.redis)


def get_task_publisher(request: Request) -> DocumentTaskPublisher:
    """Return the configured background-task publisher."""

    return cast(DocumentTaskPublisher, request.app.state.task_publisher)


def get_document_service(
    storage: Annotated[ObjectStorage, Depends(get_storage)],
    publisher: Annotated[DocumentTaskPublisher, Depends(get_task_publisher)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentService:
    """Compose the stateless document application service."""

    return DocumentService(
        repository=DocumentRepository(),
        job_repository=ProcessingJobRepository(),
        publisher=publisher,
        storage=storage,
        settings=settings,
    )


def get_processing_job_service() -> ProcessingJobService:
    """Compose the read-only processing-job service."""

    return ProcessingJobService(ProcessingJobRepository())


def get_document_analysis_service() -> DocumentAnalysisService:
    """Compose the read-only document-analysis service."""

    return DocumentAnalysisService(
        analysis_repository=DocumentAnalysisRepository(),
        document_repository=DocumentRepository(),
    )

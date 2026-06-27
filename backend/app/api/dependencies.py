"""FastAPI dependency wiring for infrastructure and services."""

from collections.abc import AsyncIterator
from typing import Annotated, cast

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import Settings, get_settings
from app.database.session import Database
from app.repositories.documents import DocumentRepository
from app.services.documents import DocumentService
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


def get_document_service(
    storage: Annotated[ObjectStorage, Depends(get_storage)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DocumentService:
    """Compose the stateless document application service."""

    return DocumentService(
        repository=DocumentRepository(),
        storage=storage,
        settings=settings,
    )

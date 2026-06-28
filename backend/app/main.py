"""FastAPI application factory and process lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.api.router import api_router
from app.config.settings import Settings, get_settings
from app.database.session import Database
from app.messaging.celery_publisher import CeleryDocumentTaskPublisher
from app.storage.local import LocalObjectStorage
from app.worker.celery_factory import create_celery


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build an independently configurable FastAPI application."""

    resolved_settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        database = Database(resolved_settings)
        storage = LocalObjectStorage(resolved_settings.upload_directory)
        celery = create_celery(resolved_settings)
        task_publisher = CeleryDocumentTaskPublisher(
            celery,
            queue_name=resolved_settings.celery_queue_name,
        )
        redis = Redis.from_url(
            resolved_settings.redis_url,
            socket_connect_timeout=(
                resolved_settings.celery_broker_connection_timeout_seconds
            ),
            socket_timeout=resolved_settings.celery_broker_connection_timeout_seconds,
        )

        try:
            await storage.initialize()
            app.state.database = database
            app.state.storage = storage
            app.state.task_publisher = task_publisher
            app.state.redis = redis
            yield
        finally:
            await redis.aclose()
            await task_publisher.close()
            await database.dispose()

    application = FastAPI(
        title=resolved_settings.app_name,
        debug=resolved_settings.debug,
        version="0.1.0",
        lifespan=lifespan,
    )

    if resolved_settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=list(resolved_settings.cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Content-Type"],
        )

    application.include_router(
        api_router,
        prefix=resolved_settings.api_v1_prefix,
    )
    return application

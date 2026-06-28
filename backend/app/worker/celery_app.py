"""Celery command-line entry point."""

from app.worker.celery_factory import create_celery

celery_app = create_celery()

# Backend

Async FastAPI service for document ingestion and metadata persistence.

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
cp .env.example .env
alembic upgrade head
uvicorn app.main:create_app --factory --reload
```

In a second terminal, run the worker after Redis is available:

```bash
celery --app=app.worker.celery_app:celery_app worker \
  --loglevel=INFO --queues=documents
```

Alternatively, start the complete backend stack from the repository root:

```bash
docker compose up --build
```

The example database URL assumes a PostgreSQL database and credentials have
already been provisioned. The API does not create schemas during startup.

## Quality checks

```bash
ruff check .
ruff format --check .
mypy app
pytest
```

## REST API

- `POST /api/v1/documents` persists a PDF or CSV and queues processing.
- `GET /api/v1/documents` lists persisted document metadata.
- `GET /api/v1/documents/{document_id}` retrieves one document.
- `GET /api/v1/jobs` lists background-processing history.
- `GET /api/v1/jobs/{job_id}` retrieves durable job status.
- `GET /api/v1/health/live` checks process health.
- `GET /api/v1/health/ready` checks PostgreSQL connectivity.

## Architectural boundaries

Routes translate HTTP, services coordinate workflows and transactions,
repositories contain SQLAlchemy queries, and storage adapters persist document
bytes. A messaging adapter publishes job UUIDs to Redis through Celery. Thin
Celery tasks invoke the same service layer used by other delivery mechanisms.
PostgreSQL, rather than Celery's result backend, is the source of truth for job
status.

The upload transaction commits document metadata and a pending job before
publishing to Redis. If publication fails, the job is marked `enqueue_failed`.
There is still a failure window between the PostgreSQL commit and broker
publication; a transactional outbox will close that gap in a later hardening
phase.

The initial local storage adapter is intended only for development. It is not
durable across Kubernetes pod replacement and must be replaced by shared object
storage before horizontal scaling.

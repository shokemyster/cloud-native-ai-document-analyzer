# Backend application package

- `api/` translates HTTP requests and responses.
- `config/` validates environment-derived settings.
- `database/` owns SQLAlchemy metadata, engines, and sessions.
- `models/` defines PostgreSQL ORM models.
- `repositories/` contains database queries.
- `schemas/` defines public Pydantic API contracts.
- `services/` coordinates use cases and transaction boundaries.
- `storage/` defines object-storage contracts and adapters.

Routes depend on services; services depend on repositories and storage contracts;
adapters depend on SQLAlchemy or filesystem implementations. Future Celery tasks
will invoke services rather than duplicate application logic.

# Backend application package

- `api/` translates HTTP requests and responses.
- `application/` coordinates use cases and transactions.
- `domain/` defines business concepts and dependency contracts.
- `infrastructure/` implements contracts using PostgreSQL, Redis, object storage, and AI providers.
- `tasks/` exposes application use cases to Celery.

Dependencies should point inward: delivery and infrastructure code may depend on application and domain code, but the domain must not depend on FastAPI, Celery, or database implementations.


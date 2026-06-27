# Backend tests

- `unit/` tests domain and application behavior without external services.
- `integration/` verifies boundaries such as PostgreSQL repositories, Redis/Celery configuration, storage adapters, and API behavior.

The separation keeps fast feedback available while still testing production integrations.


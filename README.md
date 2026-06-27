# AI Document Analyzer

A production-style learning project for Docker, Kubernetes, cloud-native architecture, and operational troubleshooting.

Phase 1 establishes the repository boundaries only. Application code, dependencies, containers, and Kubernetes resources will be introduced incrementally in later phases.

## Top-level layout

- `frontend/` — browser-based React and TypeScript client.
- `backend/` — FastAPI API, Celery worker entry points, domain code, and tests.
- `deploy/` — Docker and Kubernetes deployment definitions.
- `docs/` — architecture, decisions, and operational knowledge.
- `scripts/` — small, repeatable developer and operations commands.

## Architectural direction

The project starts as a modular monolith. The API and worker will share domain and application code, while running as separate processes. This keeps deployment realistic without introducing unnecessary distributed-service boundaries.


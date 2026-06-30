"""Integration tests for FastAPI application composition."""

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.config.settings import Settings
from app.main import create_app


def build_settings(tmp_path: Path) -> Settings:
    return Settings.model_validate(
        {
            "environment": "test",
            "database_url": ("postgresql+asyncpg://unused:unused@localhost/unused"),
            "upload_directory": tmp_path / "uploads",
            "cors_origins": [],
        }
    )


def test_liveness_and_document_routes_are_exposed(tmp_path: Path) -> None:
    application = create_app(build_settings(tmp_path))

    with TestClient(application) as client:
        response = client.get("/api/v1/health/live")
        openapi: dict[str, Any] = client.get("/openapi.json").json()

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "202" in openapi["paths"]["/api/v1/documents"]["post"]["responses"]
    assert openapi["paths"]["/api/v1/documents"]["get"]
    assert openapi["paths"]["/api/v1/documents/{document_id}"]["get"]
    assert openapi["paths"]["/api/v1/documents/{document_id}/analysis"]["get"]
    assert openapi["paths"]["/api/v1/jobs"]["get"]
    assert openapi["paths"]["/api/v1/jobs/{job_id}"]["get"]

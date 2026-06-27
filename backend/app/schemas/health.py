"""Health endpoint response schema."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Machine-readable process or dependency health state."""

    status: Literal["ok"] = "ok"

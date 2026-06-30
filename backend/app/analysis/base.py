"""Provider-neutral document-analysis contracts."""

from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class AnalysisOutput(BaseModel):
    """Structured analysis generated from extracted document text."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: str = Field(min_length=1, max_length=2000)
    document_type: str = Field(min_length=1, max_length=100)
    key_points: list[str] = Field(min_length=1, max_length=8)


@dataclass(frozen=True, slots=True)
class AnalysisContext:
    """Non-sensitive document metadata supplied to an analyzer."""

    filename: str
    media_type: str


@dataclass(frozen=True, slots=True)
class AnalyzerResult:
    """Provider-neutral result and usage metadata."""

    output: AnalysisOutput
    provider: str
    model_name: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class AnalyzerError(Exception):
    """Base exception for AI provider and response failures."""


class AnalyzerConfigurationError(AnalyzerError):
    """Raised when worker-side analyzer configuration is incomplete."""


class AnalyzerResponseError(AnalyzerError):
    """Raised when the provider returns no usable structured output."""


class DocumentAnalyzer(Protocol):
    """Generate structured analysis without exposing provider SDK types."""

    @property
    def provider(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    async def analyze(
        self,
        text: str,
        *,
        context: AnalysisContext,
    ) -> AnalyzerResult: ...

    async def close(self) -> None: ...

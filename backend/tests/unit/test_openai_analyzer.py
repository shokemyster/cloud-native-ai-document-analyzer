"""Mocked tests for the OpenAI structured-analysis adapter."""

from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from openai import AsyncOpenAI

from app.analysis.base import AnalysisContext, AnalysisOutput, AnalyzerError
from app.analysis.openai import OpenAIDocumentAnalyzer


class FakeResponses:
    def __init__(self, failure_detail: str | None = None) -> None:
        self.arguments: dict[str, Any] | None = None
        self.failure_detail = failure_detail

    async def parse(self, **arguments: Any) -> SimpleNamespace:
        self.arguments = arguments
        if self.failure_detail is not None:
            raise RuntimeError(self.failure_detail)
        return SimpleNamespace(
            output_parsed=AnalysisOutput(
                summary="Concise summary",
                document_type="report",
                key_points=["Key point"],
            ),
            model="confirmed-model",
            usage=SimpleNamespace(input_tokens=25, output_tokens=12),
        )


class FakeOpenAIClient:
    def __init__(self, failure_detail: str | None = None) -> None:
        self.responses = FakeResponses(failure_detail)
        self.closed = False

    async def close(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_openai_analyzer_returns_normalized_structured_result() -> None:
    client = FakeOpenAIClient()
    instructions = uuid4().hex
    source_text = uuid4().hex
    analyzer = OpenAIDocumentAnalyzer(
        api_key=None,
        instructions=instructions,
        model="configured-model",
        max_output_tokens=600,
        timeout_seconds=60,
        max_retries=2,
        client=cast(AsyncOpenAI, client),
    )

    result = await analyzer.analyze(
        source_text,
        context=AnalysisContext(filename="fixture.csv", media_type="text/csv"),
    )
    await analyzer.close()

    assert result.output.summary == "Concise summary"
    assert result.output.key_points == ["Key point"]
    assert result.model_name == "confirmed-model"
    assert result.input_tokens == 25
    assert result.output_tokens == 12
    assert client.responses.arguments is not None
    assert client.responses.arguments["instructions"] == instructions
    assert source_text in client.responses.arguments["input"]
    assert client.responses.arguments["store"] is False
    assert client.responses.arguments["text_format"] is AnalysisOutput
    assert client.closed is True


@pytest.mark.asyncio
async def test_openai_analyzer_sanitizes_provider_failures() -> None:
    provider_detail = uuid4().hex
    client = FakeOpenAIClient(failure_detail=provider_detail)
    analyzer = OpenAIDocumentAnalyzer(
        api_key=None,
        instructions=uuid4().hex,
        model="configured-model",
        max_output_tokens=600,
        timeout_seconds=60,
        max_retries=2,
        client=cast(AsyncOpenAI, client),
    )

    with pytest.raises(AnalyzerError) as error:
        await analyzer.analyze(
            uuid4().hex,
            context=AnalysisContext(filename="fixture.csv", media_type="text/csv"),
        )

    assert str(error.value) == "OpenAI analysis request failed"
    assert provider_detail not in str(error.value)
    assert error.value.__suppress_context__ is True

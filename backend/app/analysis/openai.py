"""OpenAI Responses API document-analyzer adapter."""

from openai import AsyncOpenAI

from app.analysis.base import (
    AnalysisContext,
    AnalysisOutput,
    AnalyzerConfigurationError,
    AnalyzerError,
    AnalyzerResponseError,
    AnalyzerResult,
)


class OpenAIDocumentAnalyzer:
    """Generate structured document analysis through OpenAI."""

    def __init__(
        self,
        *,
        api_key: str | None,
        instructions: str | None,
        model: str,
        max_output_tokens: int,
        timeout_seconds: int,
        max_retries: int,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self._client = client or (
            AsyncOpenAI(
                api_key=api_key,
                timeout=timeout_seconds,
                max_retries=max_retries,
            )
            if api_key
            else None
        )
        self._instructions = instructions
        self._model = model
        self._max_output_tokens = max_output_tokens

    @property
    def provider(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    async def analyze(
        self,
        text: str,
        *,
        context: AnalysisContext,
    ) -> AnalyzerResult:
        if self._client is None or not self._instructions:
            raise AnalyzerConfigurationError(
                "OpenAI worker credentials or instructions are missing"
            )

        try:
            response = await self._client.responses.parse(
                model=self._model,
                instructions=self._instructions,
                input=text,
                text_format=AnalysisOutput,
                max_output_tokens=self._max_output_tokens,
                store=False,
            )
        except Exception:
            raise AnalyzerError("OpenAI analysis request failed") from None

        parsed = response.output_parsed
        if parsed is None:
            raise AnalyzerResponseError("OpenAI returned no structured analysis")

        usage = response.usage
        return AnalyzerResult(
            output=parsed,
            provider="openai",
            model_name=response.model,
            input_tokens=usage.input_tokens if usage else None,
            output_tokens=usage.output_tokens if usage else None,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()

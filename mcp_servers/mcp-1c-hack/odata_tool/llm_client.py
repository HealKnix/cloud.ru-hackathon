from __future__ import annotations

import json
import re
import time
from typing import Any, List, Tuple

import httpx
from opentelemetry import trace

try:  # prefer tenacity, but allow running without it in minimal environments
    from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
except ImportError:  # pragma: no cover - fallback when dependency is missing
    def retry(*_args, **_kwargs):  # type: ignore
        def decorator(func):
            return func
        return decorator

    def retry_if_exception_type(*_args, **_kwargs):  # type: ignore
        return lambda exc: True

    def stop_after_attempt(*_args, **_kwargs):  # type: ignore
        return None

    def wait_exponential(*_args, **_kwargs):  # type: ignore
        return None

from .exceptions import LLMClientError, PlanParseError
from .models import QueryPlan
from .prompts import build_prompt

tracer = trace.get_tracer(__name__)

_JSON_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


def _extract_llm_text(payload: dict) -> str:
    if "choices" in payload and payload["choices"]:
        choice = payload["choices"][0]
        message = choice.get("message") or {}
        if "content" in message and isinstance(message["content"], str):
            return message["content"]
        if "text" in choice and isinstance(choice["text"], str):
            return choice["text"]
    if "result" in payload and isinstance(payload["result"], str):
        return payload["result"]
    raise LLMClientError("Unexpected LLM response format, no text content found")


def _parse_structured_plan(text: str) -> QueryPlan:
    if not text or not text.strip():
        raise PlanParseError("LLM response is empty")
    raw = text.strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = _JSON_PATTERN.search(raw)
        if not match:
            raise PlanParseError("LLM response is not valid JSON")
        parsed = json.loads(match.group(0))
    try:
        return QueryPlan.model_validate(parsed)
    except Exception as exc:  # noqa: BLE001
        raise PlanParseError(f"Invalid plan structure: {exc}") from exc


class LLMClient:
    """Retry-enabled async client for chat completions."""

    def __init__(
        self,
        api_key: str,
        model_id: str,
        base_url: str | None = None,
        timeout: float = 30.0,
        auth_scheme: str = "Bearer",
        extra_headers: dict | None = None,
        use_structured_output: bool = True,
    ) -> None:
        self.api_key = api_key
        self.model_id = model_id
        self.base_url = (base_url or "https://foundation-models.api.cloud.ru/v1").rstrip("/")
        self.timeout = timeout
        self.auth_scheme = auth_scheme or "Bearer"
        self.extra_headers = extra_headers or {}
        self.use_structured_output = use_structured_output

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
    )
    async def generate_plan(
        self, user_query: str, candidates: List[Any]
    ) -> Tuple[QueryPlan, int, str]:
        if not self.api_key:
            raise LLMClientError("API_KEY is not set")
        if not self.model_id:
            raise LLMClientError("CLOUD_MODEL_ID is not set")

        messages = build_prompt(user_query, candidates)
        headers = {
            "Authorization": f"{self.auth_scheme} {self.api_key}",
            "Content-Type": "application/json",
        }
        headers.update(self.extra_headers)
        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model_id,
            "messages": messages,
            "temperature": 0,
        }
        if self.use_structured_output:
            payload["response_format"] = {"type": "json_object"}

        with tracer.start_as_current_span("llm_plan") as span:
            span.set_attribute("model_id", self.model_id)
            span.set_attribute("structured_output", bool(self.use_structured_output))
            start = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    if (
                        response.status_code >= 400
                        and self.use_structured_output
                        and "response_format" in payload
                    ):
                        span.set_attribute("structured_output_retry", True)
                        retry_payload = dict(payload)
                        retry_payload.pop("response_format", None)
                        response = await client.post(url, headers=headers, json=retry_payload)
            except Exception as exc:  # noqa: BLE001
                raise LLMClientError(f"LLM request failed: {exc}") from exc
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            span.set_attribute("status_code", response.status_code)
            span.set_attribute("elapsed_ms", elapsed_ms)

        if response.status_code >= 400:
            detail = response.text
            raise LLMClientError(f"LLM HTTP {response.status_code}: {detail}")

        try:
            payload_json = response.json()
        except Exception as exc:  # noqa: BLE001
            raise LLMClientError(f"Cannot decode LLM response JSON: {exc}") from exc

        text = _extract_llm_text(payload_json)
        try:
            plan = _parse_structured_plan(text)
        except PlanParseError as exc:
            raise PlanParseError(f"{exc}. Raw: {text}") from exc
        return plan, elapsed_ms, text

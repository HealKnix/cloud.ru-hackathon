from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Tuple
from urllib.parse import parse_qsl

import aiohttp
import httpx
from opentelemetry import trace
from pydantic import BaseModel, ConfigDict, Field
from yarl import URL

from odata_tool import (
    Candidate,
    FilterCondition,
    FilterGroup,
    FilterOperator,
    ODataFilterBuilder,
    ODataUrlBuilder,
    QueryPlan as StructuredPlan,
    choose_candidates,
    build_prompt,
)
from odata_tool.exceptions import LLMClientError, ODataClientError, PlanParseError
from odata_tool.llm_client import LLMClient
from odata_tool.url_builder import normalize_entity_name

tracer = trace.get_tracer(__name__)


class QueryPlan(BaseModel):
    """Legacy lightweight plan with plain params dictionary."""

    entity: str
    params: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="ignore")

    @classmethod
    def model_validate(cls, obj: Any, *args: Any, **kwargs: Any) -> "QueryPlan":  # type: ignore[override]
        if isinstance(obj, dict) and isinstance(obj.get("params"), str):
            obj = dict(obj)
            obj["params"] = {k: v for k, v in parse_qsl(obj["params"], keep_blank_values=True)}
        return super().model_validate(obj, *args, **kwargs)


_JSON_PATTERN = re.compile(r"\{.*\}", re.DOTALL)


def _structured_to_legacy(plan: StructuredPlan) -> QueryPlan:
    builder = ODataFilterBuilder()
    params: Dict[str, Any] = {}
    if plan.filter_group:
        filter_str = builder.build(plan.filter_group)
        if filter_str:
            params["$filter"] = filter_str
    if plan.select:
        params["$select"] = ",".join(plan.select)
    if plan.top:
        params["$top"] = plan.top
    if plan.orderby:
        params["$orderby"] = ",".join(f"{field} {direction}" for field, direction in plan.orderby)
    if plan.expand:
        params["$expand"] = ",".join(plan.expand)
    return QueryPlan(entity=plan.entity, params=params)


def parse_plan(text: str) -> QueryPlan:
    """Parse JSON plan returned by the LLM."""
    if not text or not text.strip():
        raise PlanParseError("LLM response is empty")

    raw = text.strip()
    parsed: Dict[str, Any] | None = None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = _JSON_PATTERN.search(raw)
        if not match:
            raise PlanParseError("LLM response is not valid JSON")
        parsed = json.loads(match.group(0))

    # Structured schema
    if isinstance(parsed, dict) and (
        "filter_group" in parsed or "select" in parsed or "orderby" in parsed or "top" in parsed
    ):
        structured = StructuredPlan.model_validate(parsed)
        return _structured_to_legacy(structured)

    try:
        return QueryPlan.model_validate(parsed)
    except Exception as exc:  # noqa: BLE001
        raise PlanParseError(f"Invalid plan structure: {exc}") from exc


def normalize_params(params: Dict[str, Any] | None) -> Dict[str, Any]:
    """Normalize keys to OData style ($filter, $select, ...)."""
    if params is None:
        return {"$format": "json"}

    normalized: Dict[str, Any] = {}
    for key, value in params.items():
        if value in (None, ""):
            continue
        key = (key or "").strip()
        if not key:
            continue
        bare = key.lstrip("$").lower()
        if not key.startswith("$") and bare in {"filter", "select", "top", "orderby", "format", "expand"}:
            key = f"${bare}"
        if key == "$format" and not value:
            value = "json"
        if key == "$filter" and isinstance(value, str):
            value = _normalize_filter_dates(value)
        normalized[key] = value

    if "$format" not in normalized:
        normalized["$format"] = "json"
    return normalized


def build_odata_url(base_url: str, entity: str, params: Dict[str, Any] | None) -> Tuple[str, Dict[str, Any]]:
    builder = ODataUrlBuilder()
    normalized_params = normalize_params(params)
    full_url = builder.build(base_url, entity, normalized_params)
    # Return root path (without query) for backward compatibility
    root = full_url.split("?", 1)[0]
    return root, normalized_params


_DATE_RE = re.compile(
    r"(?<!datetime)"      # not after the word datetime
    r"(?<!')"             # not already inside datetime'...'
    r"'(\d{4}-\d{2}-\d{2}(?:[Tt]\d{2}:\d{2}:\d{2})?)'",  # quoted date literal
)


def _normalize_filter_dates(filter_expr: str) -> str:
    """Wrap date literals with datetime'...' if not already wrapped."""
    if "datetime'" in filter_expr.lower():
        return filter_expr

    def _repl(match: re.Match[str]) -> str:
        raw = match.group(1)
        if "T" in raw or "t" in raw:
            date_part, time_part = raw.replace("t", "T").split("T", 1)
        else:
            date_part, time_part = raw, "00:00:00"
        parts = time_part.split(":")
        while len(parts) < 3:
            parts.append("00")
        normalized_time = ":".join(parts[:3])
        normalized = f"{date_part}T{normalized_time}"
        return f"datetime'{normalized}'"

    return _DATE_RE.sub(_repl, filter_expr)


class CloudLLMClient:
    """Thin async client for chat completions with structured prompt."""

    def __init__(
        self,
        api_key: str,
        model_id: str,
        base_url: str | None = None,
        timeout: float = 30.0,
        auth_scheme: str = "Bearer",
        extra_headers: Dict[str, str] | None = None,
    ) -> None:
        self.client = LLMClient(
            api_key=api_key,
            model_id=model_id,
            base_url=base_url,
            timeout=timeout,
            auth_scheme=auth_scheme,
            extra_headers=extra_headers,
        )

    async def generate_plan(
        self, user_query: str, candidates: List[Candidate]
    ) -> Tuple[QueryPlan, int, str]:
        structured_plan, elapsed_ms, raw_text = await self.client.generate_plan(user_query, candidates)
        legacy_plan = _structured_to_legacy(structured_plan)
        return legacy_plan, elapsed_ms, raw_text


class ODataClient:
    """Async HTTP client for 1C OData using safe URL builder."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        timeout: float = 20.0,
    ) -> None:
        self.base_url = base_url
        self.username = username
        self.password = password
        self.timeout = timeout
        self.url_builder = ODataUrlBuilder()

    async def fetch(self, entity: str, params: Dict[str, Any]) -> Dict[str, Any]:
        normalized_params = normalize_params(params)
        try:
            full_url = self.url_builder.build(self.base_url, entity, normalized_params)
        except Exception as exc:  # noqa: BLE001
            raise ODataClientError(str(exc))

        auth = (
            aiohttp.BasicAuth(self.username or "", self.password or "", encoding="utf-8")
            if (self.username or self.password)
            else None
        )

        with tracer.start_as_current_span("odata_request") as span:
            span.set_attribute("entity", entity)
            span.set_attribute("params", str(normalized_params))
            print(f"[OData request] {full_url}")
            start = time.perf_counter()
            try:
                async with aiohttp.ClientSession(
                    auth=auth,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as session:
                    async with session.get(
                        URL(full_url, encoded=True),
                        headers={"Accept": "application/json"},
                    ) as response:
                        elapsed_ms = int((time.perf_counter() - start) * 1000)
                        span.set_attribute("status_code", response.status)
                        span.set_attribute("elapsed_ms", elapsed_ms)

                        if response.status >= 400:
                            try:
                                detail = await response.json()
                            except Exception:
                                detail = await response.text()
                            raise ODataClientError(
                                f"OData HTTP {response.status}",
                                status_code=response.status,
                                response=detail,
                                url=full_url,
                                elapsed_ms=elapsed_ms,
                                params=normalized_params,
                            )

                        try:
                            payload = await response.json()
                        except Exception as exc:  # noqa: BLE001
                            raise ODataClientError(
                                f"Failed to parse OData JSON: {exc}",
                                status_code=response.status,
                                url=full_url,
                                elapsed_ms=elapsed_ms,
                                params=normalized_params,
                            )
            except aiohttp.ClientError as exc:  # noqa: BLE001
                raise ODataClientError(f"OData request failed: {exc}", url=full_url, params=normalized_params)

        return {
            "url": full_url,
            "payload": payload,
            "elapsed_ms": elapsed_ms,
            "status_code": response.status,
            "params": normalized_params,
        }


def build_messages(user_query: str, candidates: List[Candidate]) -> List[Dict[str, str]]:
    """Compatibility wrapper to construct LLM prompts."""
    return build_prompt(user_query, candidates)

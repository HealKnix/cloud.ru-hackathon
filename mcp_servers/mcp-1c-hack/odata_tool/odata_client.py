from __future__ import annotations

import asyncio
import time
from typing import Any, Dict

import aiohttp
from opentelemetry import trace

try:  # prefer tenacity but allow running without it
    from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
except ImportError:  # pragma: no cover
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

from .exceptions import ODataClientError
from .filter_builder import ODataFilterBuilder
from .models import QueryPlan
from .url_builder import ODataUrlBuilder

tracer = trace.get_tracer(__name__)


class ODataClient:
    """Async HTTP client for 1C OData with retry and safe URL building."""

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
        self.filter_builder = ODataFilterBuilder()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=5),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
    )
    async def fetch(self, plan: QueryPlan, extra_params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        if plan.filter_group:
            filter_str = self.filter_builder.build(plan.filter_group)
            if filter_str:
                params["$filter"] = filter_str
        if plan.select:
            params["$select"] = ",".join(plan.select)
        if plan.top:
            params["$top"] = plan.top
        if plan.orderby:
            order_parts = [f"{field} {direction}" for field, direction in plan.orderby]
            params["$orderby"] = ",".join(order_parts)
        if plan.expand:
            params["$expand"] = ",".join(plan.expand)
        params.update(extra_params or {})

        try:
            full_url = self.url_builder.build(self.base_url, plan.entity, params)
        except Exception as exc:  # noqa: BLE001
            raise ODataClientError(str(exc))

        auth = (
            aiohttp.BasicAuth(self.username or "", self.password or "", encoding="utf-8")
            if (self.username or self.password)
            else None
        )

        with tracer.start_as_current_span("odata_request") as span:
            span.set_attribute("entity", plan.entity)
            span.set_attribute("params", str(params))
            print(f"[OData request] {full_url}")
            start = time.perf_counter()
            try:
                async with aiohttp.ClientSession(
                    auth=auth,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as session:
                    async with session.get(
                        full_url,
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
                                params=params,
                            )

                        try:
                            payload = await response.json()
                        except Exception as exc:  # noqa: BLE001
                            raise ODataClientError(
                                f"Failed to parse OData JSON: {exc}",
                                status_code=response.status,
                                url=full_url,
                                elapsed_ms=elapsed_ms,
                                params=params,
                            )
            except aiohttp.ClientError as exc:  # noqa: BLE001
                raise ODataClientError(f"OData request failed: {exc}", url=full_url, params=params)

        return {
            "url": full_url,
            "payload": payload,
            "elapsed_ms": elapsed_ms,
            "status_code": response.status,
            "params": params,
        }

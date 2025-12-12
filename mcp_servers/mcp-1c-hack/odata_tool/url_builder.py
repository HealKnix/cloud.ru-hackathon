from __future__ import annotations

from urllib.parse import quote

from .exceptions import ODataClientError


def normalize_entity_name(entity: str) -> str:
    """Ensure entity includes a delimiter after prefix (Document_, Catalog_, ...)."""
    if not entity:
        return entity
    entity = entity.strip()
    prefixes = ("Catalog", "Document", "InformationRegister", "AccumulationRegister", "ChartOfAccounts")
    for prefix in prefixes:
        if entity.lower().startswith(prefix.lower()):
            rest = entity[len(prefix) :].lstrip("_")
            return f"{prefix}_{rest}"
    return entity


class ODataUrlBuilder:
    """Safe OData URL builder with controlled encoding."""

    ODATA_KEYWORDS = {"eq", "ne", "gt", "lt", "ge", "le", "and", "or", "not"}
    SAFE_CHARS = "$'(),=<>:+-"  # keep operators/quotes/parens intact

    def build(self, base_url: str, entity: str, params: dict | None) -> str:
        if not base_url:
            raise ODataClientError("OData base URL is not configured")
        if not entity:
            raise ODataClientError("OData entity is not specified")

        normalized_params = dict(params or {})
        if "$format" not in normalized_params:
            normalized_params["$format"] = "json"

        base = base_url.rstrip("/")
        lower = base.lower()
        if lower.endswith("/odata/standard.odata"):
            normalized_base = base
        elif lower.endswith("/odata"):
            normalized_base = f"{base}/standard.odata"
        else:
            normalized_base = f"{base}/odata/standard.odata"

        fixed_entity = normalize_entity_name(entity)
        encoded_entity = quote(fixed_entity, safe="$()_-~.")
        root = f"{normalized_base}/{encoded_entity}"

        query_parts: list[str] = []
        for key, value in normalized_params.items():
            if value is None or value == "":
                continue
            if key == "$filter" and isinstance(value, str):
                encoded_value = self._encode_filter(value)
            else:
                encoded_value = quote(str(value), safe="$,:'")
            encoded_key = quote(str(key), safe="$")
            query_parts.append(f"{encoded_key}={encoded_value}")

        if not query_parts:
            return root
        return f"{root}?{'&'.join(query_parts)}"

    def _encode_filter(self, filter_str: str) -> str:
        # Encode non-ASCII while keeping operators, quotes, parentheses, commas
        return quote(filter_str, safe=self.SAFE_CHARS)

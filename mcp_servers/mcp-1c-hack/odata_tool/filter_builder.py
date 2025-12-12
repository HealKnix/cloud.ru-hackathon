from __future__ import annotations

import datetime as dt
from typing import Any

from .models import FilterCondition, FilterGroup, FilterOperator


class ODataFilterBuilder:
    """Builds OData $filter strings from structured filter groups."""

    def build(self, group: FilterGroup | None) -> str:
        if not group or not group.conditions:
            return ""
        return self._build_group(group)

    def _build_group(self, group: FilterGroup) -> str:
        parts: list[str] = []
        for condition in group.conditions:
            if isinstance(condition, FilterGroup):
                nested = self._build_group(condition)
                if nested:
                    parts.append(f"({nested})")
            else:
                parts.append(self._render_condition(condition))
        if not parts:
            return ""
        if len(parts) == 1:
            return parts[0]
        separator = f" {group.logic} "
        wrapped = [p if (p.startswith("(") and p.endswith(")")) else f"({p})" for p in parts]
        return separator.join(wrapped)

    def _render_condition(self, cond: FilterCondition) -> str:
        operator = cond.operator.value if isinstance(cond.operator, FilterOperator) else str(cond.operator)
        value = self._format_value(cond.value, cond.value_type)
        return f"{cond.field} {operator} {value}"

    def _format_value(self, value: Any, value_type: str) -> str:
        if value_type == "string":
            escaped = str(value).replace("'", "''")
            return f"'{escaped}'"
        if value_type == "datetime":
            normalized = self._normalize_datetime(value)
            return f"datetime'{normalized}'"
        if value_type == "guid":
            return f"guid'{value}'"
        if value_type == "boolean":
            return "true" if bool(value) else "false"
        # numeric or fallback
        return str(value)

    def _normalize_datetime(self, value: Any) -> str:
        """
        Normalize datetime-like inputs to YYYY-MM-DDTHH:MM:SS.
        Supports:
        - 2024-01-15
        - 2024-01-15T10:30
        - 2024-01-15T10:30:45
        - 15.01.2024
        - 15.01.2024 10:20[:30]
        """
        if isinstance(value, dt.datetime):
            return value.replace(microsecond=0).isoformat()
        if isinstance(value, dt.date):
            return dt.datetime.combine(value, dt.time.min).isoformat()

        raw = str(value).strip()
        patterns = [
            ("%Y-%m-%dT%H:%M:%S", False),
            ("%Y-%m-%dT%H:%M", True),
            ("%Y-%m-%d", True),
            ("%d.%m.%Y %H:%M:%S", False),
            ("%d.%m.%Y %H:%M", False),
            ("%d.%m.%Y", True),
        ]
        for fmt, add_time in patterns:
            try:
                parsed = dt.datetime.strptime(raw, fmt)
                if add_time:
                    parsed = parsed.replace(hour=0, minute=0, second=0, microsecond=0)
                return parsed.replace(microsecond=0).isoformat()
            except ValueError:
                continue
        # fallback: if string already contains T maybe just ensure seconds
        if "T" in raw:
            parts = raw.split("T", 1)
            date_part = parts[0]
            time_part = parts[1] if len(parts) > 1 else "00:00:00"
            time_bits = time_part.split(":")
            while len(time_bits) < 3:
                time_bits.append("00")
            normalized_time = ":".join(time_bits[:3])
            return f"{date_part}T{normalized_time}"
        raise ValueError(f"Unrecognized datetime format: {value}")

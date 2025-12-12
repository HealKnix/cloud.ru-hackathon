from __future__ import annotations

import re
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FilterOperator(str, Enum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    LT = "lt"
    GE = "ge"
    LE = "le"


class FilterCondition(BaseModel):
    """Atomic filter condition."""

    field: str = Field(..., description="Field name from 1C metadata")
    operator: FilterOperator
    value: str | int | float | bool | None
    value_type: Literal["string", "number", "boolean", "datetime", "guid"] = "string"


class FilterGroup(BaseModel):
    """Group of conditions combined with logical operator."""

    logic: Literal["and", "or"] = "and"
    conditions: list["FilterCondition | FilterGroup"]


class QueryPlan(BaseModel):
    """Structured OData plan."""

    entity: str = Field(..., description="Full entity name, e.g. Catalog_Номенклатура")
    filter_group: FilterGroup | None = None
    select: list[str] = Field(default_factory=list)
    orderby: list[tuple[str, Literal["asc", "desc"]]] = Field(default_factory=list)
    top: int | None = Field(None, ge=1, le=1000)
    expand: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="ignore")

    @field_validator("entity")
    @classmethod
    def validate_entity_format(cls, v: str) -> str:
        pattern = r"^(Catalog|Document|InformationRegister|AccumulationRegister|ChartOfAccounts)_\w+$"
        if not re.match(pattern, v):
            raise ValueError(f"Invalid entity format: {v}")
        return v

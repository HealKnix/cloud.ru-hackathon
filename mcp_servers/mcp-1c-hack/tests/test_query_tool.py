import json

import pytest

from query_tool import (
    QueryPlan,
    _normalize_filter_dates,
    build_odata_url,
    normalize_params,
    parse_plan,
)
from odata_tool.filter_builder import ODataFilterBuilder
from odata_tool.models import FilterCondition, FilterGroup, FilterOperator, QueryPlan as StructuredPlan


def test_parse_structured_plan_converts_to_legacy():
    structured = {
        "entity": "Catalog_Номенклатура",
        "filter_group": {
            "logic": "and",
            "conditions": [
                {"field": "Name", "operator": "eq", "value": "Test", "value_type": "string"}
            ],
        },
        "top": 5,
        "select": ["Name", "Code"],
    }
    plan = parse_plan(json.dumps(structured))
    assert isinstance(plan, QueryPlan)
    assert plan.entity == "Catalog_Номенклатура"
    assert plan.params["$filter"] == "Name eq 'Test'"
    assert plan.params["$top"] == 5
    assert plan.params["$select"] == "Name,Code"


def test_normalize_params_adds_format_and_prefix():
    normalized = normalize_params({"filter": "A eq B", "top": 10})
    assert normalized["$filter"] == "A eq B"
    assert normalized["$top"] == 10
    assert normalized["$format"] == "json"


def test_build_odata_url_returns_root_and_params():
    url, params = build_odata_url("https://example/odata", "Document_Sale", {"$top": 1})
    assert url == "https://example/odata/standard.odata/Document_Sale"
    assert params["$top"] == 1
    assert params["$format"] == "json"


def test_normalize_filter_dates_wraps_iso():
    src = "Date lt '2024-01-02'"
    fixed = _normalize_filter_dates(src)
    assert "datetime'2024-01-02T00:00:00'" in fixed


def test_filter_builder_handles_boolean_and_nested():
    group = FilterGroup(
        logic="or",
        conditions=[
            FilterCondition(field="Status", operator=FilterOperator.EQ, value=1, value_type="number"),
            FilterGroup(
                logic="and",
                conditions=[
                    FilterCondition(field="Price", operator=FilterOperator.GT, value=100, value_type="number"),
                    FilterCondition(field="Active", operator=FilterOperator.EQ, value=True, value_type="boolean"),
                ],
            ),
        ],
    )
    built = ODataFilterBuilder().build(group)
    assert built == "(Status eq 1) or ((Price gt 100) and (Active eq true))"

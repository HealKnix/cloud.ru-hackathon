import pytest

from odata_tool.filter_builder import ODataFilterBuilder
from odata_tool.models import FilterCondition, FilterGroup, FilterOperator


@pytest.mark.parametrize(
    "group,expected",
    [
        (
            FilterGroup(logic="and", conditions=[FilterCondition(field="Name", operator=FilterOperator.EQ, value="Test", value_type="string")]),
            "Name eq 'Test'",
        ),
        (
            FilterGroup(
                logic="and",
                conditions=[FilterCondition(field="Name", operator=FilterOperator.EQ, value="It's test", value_type="string")],
            ),
            "Name eq 'It''s test'",
        ),
        (
            FilterGroup(
                logic="and",
                conditions=[
                    FilterCondition(field="Date", operator=FilterOperator.LT, value="2024-01-15", value_type="datetime")
                ],
            ),
            "Date lt datetime'2024-01-15T00:00:00'",
        ),
        (
            FilterGroup(
                logic="and",
                conditions=[
                    FilterCondition(field="Наименование", operator=FilterOperator.EQ, value="Товар", value_type="string")
                ],
            ),
            "Наименование eq 'Товар'",
        ),
        (
            FilterGroup(
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
            ),
            "(Status eq 1) or ((Price gt 100) and (Active eq true))",
        ),
    ],
)
def test_filter_builder(group, expected):
    assert ODataFilterBuilder().build(group) == expected

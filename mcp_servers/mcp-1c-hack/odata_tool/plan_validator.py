from __future__ import annotations

from typing import Dict, Iterable, List, Set

from thefuzz import fuzz, process

from .models import FilterCondition, FilterGroup, QueryPlan


class PlanValidator:
    def __init__(self, metadata: List[Dict]) -> None:
        self.entities = {f"{item.get('type')}_{item.get('name')}" for item in metadata}
        self.fields_by_entity = self._build_fields_index(metadata)

    def _build_fields_index(self, metadata: Iterable[Dict]) -> Dict[str, Set[str]]:
        index: Dict[str, Set[str]] = {}
        for item in metadata:
            entity = f"{item.get('type')}_{item.get('name')}"
            fields = item.get("fields") or []
            index[entity] = set(fields)
        return index

    def validate(self, plan: QueryPlan) -> List[str]:
        errors: List[str] = []
        if plan.entity not in self.entities:
            errors.append(f"Unknown entity: {plan.entity}")

        valid_fields = self.fields_by_entity.get(plan.entity, set())
        if plan.filter_group:
            errors.extend(self._check_fields(plan.filter_group, valid_fields))

        for field in plan.select:
            if valid_fields and field not in valid_fields:
                errors.append(f"Unknown field in select: {field}")

        for field, _direction in plan.orderby:
            if valid_fields and field not in valid_fields:
                errors.append(f"Unknown field in orderby: {field}")

        return errors

    def _check_fields(self, group: FilterGroup, valid_fields: Set[str]) -> List[str]:
        issues: List[str] = []
        for cond in group.conditions:
            if isinstance(cond, FilterGroup):
                issues.extend(self._check_fields(cond, valid_fields))
            elif valid_fields and cond.field not in valid_fields:
                issues.append(f"Unknown field in filter: {cond.field}")
        return issues

    def suggest_fixes(self, plan: QueryPlan, errors: List[str]) -> QueryPlan:
        if not errors:
            return plan

        valid_fields = self.fields_by_entity.get(plan.entity, set())
        if not valid_fields:
            return plan

        def _fix_field(name: str) -> str:
            best = process.extractOne(name, list(valid_fields), scorer=fuzz.WRatio)
            return best[0] if best else name

        if plan.filter_group:
            self._fix_group(plan.filter_group, _fix_field)

        plan.select = [(_fix_field(f) if f not in valid_fields else f) for f in plan.select]
        plan.orderby = [
            (_fix_field(field) if field not in valid_fields else field, direction) for field, direction in plan.orderby
        ]
        return plan

    def _fix_group(self, group: FilterGroup, fixer) -> None:
        for cond in group.conditions:
            if isinstance(cond, FilterGroup):
                self._fix_group(cond, fixer)
            else:
                cond.field = fixer(cond.field)

from __future__ import annotations

from typing import Any, Literal, Self

from pydantic import BaseModel, Field, model_validator

RuleType = Literal[
    "age",
    "income",
    "gender",
    "state",
    "caste_category",
    "occupation",
    "is_farmer",
    "land_holding_acres",
    "education_level",
    "family_size",
    "has_disability",
    "religion",
    "marital_status",
    "employment_status",
    "disability_percentage",
    "custom",
]

OperatorType = Literal["eq", "neq", "lt", "lte", "gt", "gte", "in", "not_in", "between", "exists"]

_SCALAR_OPS: frozenset[str] = frozenset({"eq", "neq", "lt", "lte", "gt", "gte"})
_LIST_OPS: frozenset[str] = frozenset({"in", "not_in"})
_RANGE_OPS: frozenset[str] = frozenset({"between"})


class RuleValue(BaseModel):
    """Polymorphic value container — exactly one shape set per instance."""

    value: Any | None = None  # scalar: int, float, str, bool
    min: float | None = None  # lower bound for 'between'
    max: float | None = None  # upper bound for 'between'
    in_: list[str] | None = Field(None, alias="in")  # set for 'in' / 'not_in'

    model_config = {"populate_by_name": True}


class EligibilityRule(BaseModel):
    rule_type: RuleType
    operator: OperatorType
    value: RuleValue
    logic_group: int = 0
    group_operator: Literal["AND", "OR"] = "AND"
    is_required: bool = True
    description: str = Field(..., max_length=200)
    confidence: float = Field(..., ge=0.0, le=1.0)

    @model_validator(mode="after")
    def operator_value_compatible(self) -> Self:
        op = self.operator
        v = self.value
        if op in _SCALAR_OPS:
            if v.value is None:
                raise ValueError(f"operator '{op}' requires a scalar 'value' field")
        elif op in _LIST_OPS:
            if v.in_ is None:
                raise ValueError(f"operator '{op}' requires an 'in' field")
            if len(v.in_) == 0:
                raise ValueError(f"operator '{op}' requires a non-empty 'in' list")
        elif op in _RANGE_OPS:
            if v.min is None or v.max is None:
                raise ValueError("operator 'between' requires both 'min' and 'max'")
            if v.min >= v.max:
                raise ValueError("'between' requires min < max")
        return self


class SchemeContext(BaseModel):
    """Contextual metadata passed alongside eligibility text for better extraction."""

    scheme_name: str = ""
    ministry: str = ""
    level: str = "central"
    state: str | None = None


class ExtractionResult(BaseModel):
    rules: list[EligibilityRule]
    extraction_notes: str | None = None
    has_unstructured_remainder: bool = False
    unstructured_remainder: str | None = None
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    # Pipeline-internal failure flags — set by exception handlers, never by the LLM.
    failed: bool = False
    failure_reason: str | None = None

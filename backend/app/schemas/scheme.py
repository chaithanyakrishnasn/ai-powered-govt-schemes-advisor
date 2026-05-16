"""Pydantic schemas for schemes."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict


class SchemeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    name: str
    level: str
    state: str | None = None
    categories: list[str]
    benefit_type: str | None = None
    benefit_amount_min: float | None = None
    benefit_amount_max: float | None = None
    ministry: str | None = None
    application_url: str | None = None


class PaginatedSchemes(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    items: list[SchemeListItem]
    total: int
    page: int
    size: int
    pages: int


class EligibilityRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rule_type: str
    operator: str
    value: dict[str, Any]
    logic_group: int
    is_required: bool
    description: str
    confidence: float


class SchemeDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name: str
    description: str | None = None
    ministry: str | None = None
    level: str
    state: str | None = None
    categories: list[str]
    benefit_type: str | None = None
    benefit_amount_min: float | None = None
    benefit_amount_max: float | None = None
    benefit_description: str | None = None
    application_url: str | None = None
    application_mode: str | None = None
    documents_required: list[str]
    raw_eligibility_text: str | None = None
    eligibility_rules: list[EligibilityRuleResponse]
    source_url: str
    last_updated: date | None = None

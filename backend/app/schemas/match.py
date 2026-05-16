"""Pydantic schemas for matching requests and responses."""

from __future__ import annotations

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.profile import UserProfileCreate
from app.services.matching.llm_reranker import SchemeExplanation
from app.services.matching.scheme_matcher import EligibilityStatus


class MatchRequest(BaseModel):
    profile_id: UUID | None = None
    profile: UserProfileCreate | None = None
    query: str | None = None
    explain: bool = False
    language: str = "en"
    max_results: int = Field(default=20, le=50)
    include_ineligible: bool = False

    @model_validator(mode="after")
    def require_profile_or_id(self) -> Self:
        if not self.profile_id and not self.profile:
            raise ValueError("Provide either profile_id or profile")
        return self


class SchemeResultItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    scheme_id: int
    slug: str
    name: str
    status: EligibilityStatus
    score: float
    semantic_similarity: float | None = None
    combined_score: float | None = None
    level: str
    state: str | None = None
    categories: list[str]
    benefit_type: str | None = None
    benefit_description: str | None = None
    application_url: str | None = None
    missing_fields: list[str]


class PipelineStats(BaseModel):
    stage1_candidates: int
    stage2_reranked: bool
    stage3_explained: bool
    total_latency_ms: float
    stage3_tokens: int | None = None


class MatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    profile_id: UUID | None
    query: str | None
    total_candidates: int
    results: list[SchemeResultItem]
    explanations: list[SchemeExplanation] | None = None
    pipeline_stats: PipelineStats

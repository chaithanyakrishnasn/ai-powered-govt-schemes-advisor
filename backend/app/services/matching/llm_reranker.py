from __future__ import annotations

import time
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.db.models import Scheme
from app.schemas.user_profile import UserProfile
from app.services.llm.gemini import GeminiClient
from app.services.matching.prompts import generate_user_prompt, get_system_prompt
from app.services.matching.scheme_matcher import SchemeMatchResult


class SchemeAssessment(BaseModel):
    slug: str
    final_rank: int
    eligibility_verdict: Literal[
        "eligible", "likely_eligible", "need_more_info", "not_eligible"
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str = Field(max_length=300)
    key_benefits: list[str] = Field(max_length=3)
    action_steps: list[str] = Field(max_length=3)
    missing_info: list[str] = Field(max_length=3)
    custom_rule_assessment: str | None = Field(default=None, max_length=150)


class RerankResponse(BaseModel):
    assessments: list[SchemeAssessment]


class SchemeExplanation(BaseModel):
    scheme_id: int
    slug: str
    name: str
    final_rank: int
    eligibility_verdict: Literal[
        "eligible", "likely_eligible", "need_more_info", "not_eligible"
    ]
    confidence: float
    explanation: str
    key_benefits: list[str]
    action_steps: list[str]
    missing_info: list[str]
    custom_rule_assessment: str | None = None


class LLMRerankerResult(BaseModel):
    explanations: list[SchemeExplanation]
    model_used: str
    input_tokens: int
    output_tokens: int
    latency_ms: float


class LLMReranker:
    def __init__(
        self,
        gemini_client: GeminiClient,
        session: AsyncSession,
        model: str | None = None,
    ):
        self.client = gemini_client
        self.session = session
        self.model = model or settings.GEMINI_MODEL_FAST
        self.input_tokens = 0
        self.output_tokens = 0

    async def rerank_and_explain(
        self,
        profile: UserProfile,
        candidates: list[SchemeMatchResult],
        *,
        language: str = "en",
        top_n: int = 10,
    ) -> LLMRerankerResult:
        candidate_schemes = await self._get_schemes_from_results(candidates)
        schemes_map = {s.id: s for s in candidate_schemes}

        profile_summary = self._create_profile_summary(profile)
        schemes_block = self._create_schemes_block(candidates, schemes_map)
        json_schema = RerankResponse.model_json_schema()

        system_prompt = get_system_prompt(language=language)
        user_prompt = generate_user_prompt(
            profile_summary, schemes_block, str(json_schema), top_n
        )

        start_time = time.monotonic()

        response = await self.client.instructor_client.chat.completions.create(
            model=self.model,
            response_model=RerankResponse,
            max_retries=2,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            config={"temperature": 0.2},
        )

        latency_ms = (time.monotonic() - start_time) * 1000

        validated_response, warnings = self.validate_reranker_response(
            response, candidates
        )

        self.input_tokens = len(user_prompt) // 4
        self.output_tokens = len(validated_response.model_dump_json()) // 4

        explanations = self._create_explanations(validated_response, candidates)

        return LLMRerankerResult(
            explanations=explanations,
            model_used=self.model,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            latency_ms=latency_ms,
        )

    async def _get_schemes_from_results(
        self, results: list[SchemeMatchResult]
    ) -> list[Scheme]:
        scheme_ids = [r.scheme_id for r in results]
        q = select(Scheme).where(Scheme.id.in_(scheme_ids))
        result = await self.session.execute(q)
        return list(result.scalars().all())

    def _create_profile_summary(self, profile: UserProfile) -> str:
        parts = []
        if profile.age:
            parts.append(f"Age: {profile.age}")
        if profile.gender:
            parts.append(f"Gender: {profile.gender}")
        if profile.state:
            parts.append(f"State: {profile.state}")
        if profile.occupation:
            parts.append(f"Occupation: {profile.occupation}")
        if profile.land_holding_acres:
            parts.append(f"Land: {profile.land_holding_acres} acres")
        if profile.annual_income:
            parts.append(f"Annual Income: ₹{profile.annual_income:,.0f}")
        if profile.caste_category:
            parts.append(f"Caste: {profile.caste_category}")
        return ", ".join(parts)

    def _create_schemes_block(
        self, candidates: list[SchemeMatchResult], schemes_map: dict[int, Scheme]
    ) -> str:
        def get_scheme_attr(scheme_id: int, attr: str, default: str = "N/A") -> str:
            scheme = schemes_map.get(scheme_id)
            if not scheme:
                return default
            val = getattr(scheme, attr, default)
            return str(val) if val is not None else default

        return "\n\n".join(
            [
                f"Scheme #{i+1}: {c.name} [{c.slug}]\n"
                f"Status (rule-based): {c.status.value} (score: {c.score:.2f})\n"
                f"Benefits: {get_scheme_attr(c.scheme_id, 'benefit_description', 'N/A')[:200]}\n"
                f"Raw Eligibility: {get_scheme_attr(c.scheme_id, 'raw_eligibility_text', 'N/A')[:300]}\n"
                f"Custom criteria: {sum(1 for r in c.rule_evaluations if r.rule.rule_type == 'custom')} unstructured criteria present"
                for i, c in enumerate(candidates)
            ]
        )

    def validate_reranker_response(
        self,
        response: RerankResponse,
        candidates: list[SchemeMatchResult],
    ) -> tuple[RerankResponse, list[str]]:
        warnings = []

        candidate_slugs = {c.slug for c in candidates}
        validated_assessments = []

        # Ensure all slugs are valid and re-number ranks
        for i, assessment in enumerate(
            sorted(response.assessments, key=lambda x: x.final_rank)
        ):
            if assessment.slug not in candidate_slugs:
                warnings.append(f"LLM hallucinated slug: {assessment.slug}")
                continue

            assessment.final_rank = i + 1

            # Clamp confidence
            assessment.confidence = max(0.0, min(1.0, assessment.confidence))

            # Anti-hallucination guardrail for status
            original_candidate = next(
                (c for c in candidates if c.slug == assessment.slug), None
            )
            if (
                original_candidate
                and original_candidate.status == "not_eligible"
                and assessment.eligibility_verdict == "eligible"
            ):
                warnings.append(
                    f"LLM tried to upgrade NOT_ELIGIBLE scheme {assessment.slug}"
                )
                assessment.eligibility_verdict = "likely_eligible"

            validated_assessments.append(assessment)

        response.assessments = validated_assessments
        return response, warnings

    def _create_explanations(
        self, response: RerankResponse, candidates: list[SchemeMatchResult]
    ) -> list[SchemeExplanation]:
        explanations = []
        for assessment in response.assessments:
            candidate = next((c for c in candidates if c.slug == assessment.slug), None)
            if candidate:
                data = assessment.model_dump()
                data.pop("slug", None)  # Avoid multiple values for slug
                explanations.append(
                    SchemeExplanation(
                        scheme_id=candidate.scheme_id,
                        slug=candidate.slug,
                        name=candidate.name,
                        **data,
                    )
                )
        return explanations

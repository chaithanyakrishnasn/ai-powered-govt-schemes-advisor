import os
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.user_profile import UserProfile
from app.services.matching.llm_reranker import LLMReranker, RerankResponse, SchemeAssessment
from app.services.matching.scheme_matcher import EligibilityStatus, SchemeMatchResult


def make_match_result(scheme_id: int, slug:str, status: EligibilityStatus, score: float) -> SchemeMatchResult:
    return SchemeMatchResult(
        scheme_id=scheme_id,
        slug=slug,
        name=f"Scheme {scheme_id}",
        status=status,
        score=score,
        rule_evaluations=[],
    )

@pytest.mark.asyncio
async def test_llm_reranker_drops_hallucinated_slug():
    gemini_client = AsyncMock()
    response = RerankResponse(assessments=[
        SchemeAssessment(slug="real-scheme", final_rank=1, eligibility_verdict="eligible", confidence=0.9, explanation="", key_benefits=[], action_steps=[], missing_info=[]),
        SchemeAssessment(slug="fake-scheme", final_rank=2, eligibility_verdict="eligible", confidence=0.9, explanation="", key_benefits=[], action_steps=[], missing_info=[]),
    ])
    gemini_client.instructor_client.chat.completions.create = AsyncMock(return_value=response)
    
    # Mock SQLAlchemy session and result
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_session.execute.return_value = mock_result
    mock_result.scalars.return_value.all.return_value = [
        MagicMock(id=1, slug="real-scheme")
    ]
    
    reranker = LLMReranker(gemini_client, mock_session)
    candidates = [make_match_result(1, "real-scheme", EligibilityStatus.ELIGIBLE, 0.8)]
    result = await reranker.rerank_and_explain(UserProfile(), candidates)

    assert len(result.explanations) == 1
    assert result.explanations[0].slug == "real-scheme"

@pytest.mark.asyncio
async def test_llm_reranker_caps_upgrade():
    gemini_client = AsyncMock()
    response = RerankResponse(assessments=[
        SchemeAssessment(slug="not-eligible-scheme", final_rank=1, eligibility_verdict="eligible", confidence=0.9, explanation="", key_benefits=[], action_steps=[], missing_info=[])
    ])
    gemini_client.instructor_client.chat.completions.create = AsyncMock(return_value=response)
    
    reranker = LLMReranker(gemini_client, AsyncMock())
    candidates = [make_match_result(1, "not-eligible-scheme", EligibilityStatus.NOT_ELIGIBLE, 0.0)]
    result, warnings = reranker.validate_reranker_response(response, candidates)

    assert result.assessments[0].eligibility_verdict == "likely_eligible"
    assert "LLM tried to upgrade NOT_ELIGIBLE scheme" in warnings[0]

@pytest.mark.skipif(not os.environ.get("RUN_LIVE_EVAL"), reason="RUN_LIVE_EVAL not set")
@pytest.mark.asyncio
async def test_llm_reranker_live():
    from app.db.session import async_session_maker
    from app.schemas.user_profile import UserProfile
    from app.services.llm.gemini import GeminiClient

    async with async_session_maker() as session:
        gemini_client = GeminiClient()
        reranker = LLMReranker(gemini_client, session)
        
        candidates = [
            make_match_result(1, "pm-kisan", EligibilityStatus.ELIGIBLE, 0.9),
            make_match_result(2, "some-other-scheme", EligibilityStatus.LIKELY_ELIGIBLE, 0.7),
        ]
        
        profile = UserProfile(
            age=42,
            gender="male",
            state="Karnataka",
            is_farmer=True,
            land_holding_acres=2,
            annual_income=150000,
            caste_category="OBC",
        )
        
        result = await reranker.rerank_and_explain(profile, candidates)
        
        assert result.input_tokens > 0
        assert len(result.explanations) > 0
        assert "pm-kisan" in [e.slug for e in result.explanations]
        top_exp = result.explanations[0]
        assert top_exp.explanation
        assert top_exp.key_benefits
        assert top_exp.action_steps

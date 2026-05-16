from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.matching.scheme_matcher import EligibilityStatus, SchemeMatchResult
from app.services.matching.semantic_reranker import SemanticReranker


def make_match_result(scheme_id: int, status: EligibilityStatus, score: float) -> SchemeMatchResult:
    return SchemeMatchResult(
        scheme_id=scheme_id,
        slug=f"scheme-{scheme_id}",
        name=f"Scheme {scheme_id}",
        status=status,
        score=score,
        rule_evaluations=[],
    )

@pytest.mark.asyncio
async def test_reranker_preserves_status_tiers():
    # ELIGIBLE scheme with low semantic score should still be ranked above LIKELY_ELIGIBLE with high score
    candidates = [
        make_match_result(1, EligibilityStatus.LIKELY_ELIGIBLE, 0.8),
        make_match_result(2, EligibilityStatus.ELIGIBLE, 0.9),
    ]
    
    mock_retriever = AsyncMock()
    mock_retriever._embedder.embed_one = AsyncMock(return_value=[0.1] * 768)

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        MagicMock(id=1, similarity=0.9),
        MagicMock(id=2, similarity=0.1),
    ]
    mock_session.execute.return_value = mock_result

    reranker = SemanticReranker(mock_retriever, mock_session)
    reranked = await reranker.rerank("query", candidates)

    assert len(reranked) == 2
    assert reranked[0].scheme_id == 2
    assert reranked[1].scheme_id == 1

@pytest.mark.asyncio
async def test_reranker_sorts_within_tiers():
    candidates = [
        make_match_result(1, EligibilityStatus.ELIGIBLE, 0.9),
        make_match_result(2, EligibilityStatus.ELIGIBLE, 0.8),
    ]

    mock_retriever = AsyncMock()
    mock_retriever._embedder.embed_one = AsyncMock(return_value=[0.1] * 768)

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchall.return_value = [
        MagicMock(id=1, similarity=0.1), # Lower similarity
        MagicMock(id=2, similarity=0.9), # Higher similarity
    ]
    mock_session.execute.return_value = mock_result

    reranker = SemanticReranker(mock_retriever, mock_session, alpha=0.5)
    reranked = await reranker.rerank("query", candidates)
    
    # Scheme 2 should now be first due to higher combined score
    assert reranked[0].scheme_id == 2
    assert reranked[1].scheme_id == 1

@pytest.mark.asyncio
async def test_null_embedding_fallback():
    candidates = [make_match_result(1, EligibilityStatus.ELIGIBLE, 1.0)]
    
    mock_retriever = AsyncMock()
    mock_retriever._embedder.embed_one = AsyncMock(return_value=[0.1] * 768)

    mock_session = AsyncMock()
    mock_result = MagicMock()
    # DB returns no result for scheme 1, simulating a null embedding
    mock_result.fetchall.return_value = []
    mock_session.execute.return_value = mock_result
    
    reranker = SemanticReranker(mock_retriever, mock_session, alpha=0.5)
    reranked = await reranker.rerank("query", candidates)
    
    assert reranked[0].semantic_similarity == 0.5
    assert reranked[0].combined_score == 0.5 * 1.0 + 0.5 * 0.5

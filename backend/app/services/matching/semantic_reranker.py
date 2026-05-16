from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.embedding.embedder import EmbedTaskType
from app.services.embedding.retriever import SemanticRetriever
from app.services.matching.scheme_matcher import EligibilityStatus, SchemeMatchResult


class SemanticScore(BaseModel):
    scheme_id: int
    similarity: float  # 0.0–1.0 cosine similarity

class SemanticReranker:
    def __init__(self, retriever: SemanticRetriever, session: AsyncSession, alpha: float = 0.6):
        """
        Initializes the SemanticReranker.
        alpha: weight for rule score. (1-alpha) for semantic score.
               0.6/0.4 default: rule-based signal slightly dominates.
               Rationale: a scheme you're definitively eligible for
               is more valuable than a semantically similar one you may not qualify for.
        """
        self._retriever = retriever
        self._session = session
        self.alpha = alpha

    async def rerank(
        self,
        query: str,
        candidates: list[SchemeMatchResult],
    ) -> list[SchemeMatchResult]:
        """
        Re-ranks candidates by combined score within status tiers.
        Does NOT change status. Does NOT add new schemes.
        """
        if not query or not candidates:
            return candidates

        query_vec = await self._retriever._embedder.embed_one(query, task_type=EmbedTaskType.RETRIEVAL_QUERY)
        vec_literal = f"'{list(query_vec)}'::vector"

        candidate_ids = [c.scheme_id for c in candidates]
        
        stmt = text(
            f"""
            SELECT id, 1 - (embedding <=> {vec_literal}) AS similarity
            FROM schemes
            WHERE id = ANY(:candidate_ids)
            """
        )
        
        result = await self._session.execute(stmt, {"candidate_ids": candidate_ids})
        similarity_map = {row.id: row.similarity for row in result.fetchall()}

        # Group candidates by status
        grouped_candidates = defaultdict(list)
        for cand in candidates:
            similarity = similarity_map.get(cand.scheme_id)
            if similarity is None:
                # Handle NULL embedding case
                similarity = 0.5
            
            cand.semantic_similarity = similarity
            cand.combined_score = self.alpha * cand.score + (1 - self.alpha) * similarity
            grouped_candidates[cand.status].append(cand)

        # Sort each group by combined_score and flatten
        reranked_results = []
        for status in [EligibilityStatus.ELIGIBLE, EligibilityStatus.LIKELY_ELIGIBLE, EligibilityStatus.NEED_MORE_INFO, EligibilityStatus.NOT_ELIGIBLE]:
            group = sorted(grouped_candidates[status], key=lambda x: x.combined_score or -1, reverse=True)
            reranked_results.extend(group)
            
        return reranked_results

from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Scheme
from app.schemas.user_profile import UserProfile
from app.services.matching.llm_reranker import LLMReranker, SchemeExplanation
from app.services.matching.scheme_matcher import (
    EligibilityStatus,
    SchemeMatcher,
    SchemeMatchResult,
)
from app.services.matching.semantic_reranker import SemanticReranker
from app.services.matching.sql_filter import SQLEligibilityFilter
from app.services.multilingual.detector import detect_language
from app.services.multilingual.translator import QueryTranslator

logger = logging.getLogger(__name__)

class MatchingService:
    def __init__(
        self,
        session: AsyncSession,
        llm_reranker: LLMReranker | None = None,
        translator: QueryTranslator | None = None,
    ):
        self.session = session
        self.sql_filter = SQLEligibilityFilter()
        self.matcher = SchemeMatcher()
        self.semantic_reranker = SemanticReranker(None, session)  # type: ignore
        self.llm_reranker = llm_reranker
        self.translator = translator

    async def match_profile(
        self,
        profile: UserProfile,
        query: str | None = None,
        *,
        max_results: int = 20,
        include_ineligible: bool = False,
        explain: bool = False,
        language: str = "en",
    ) -> tuple[list[SchemeMatchResult], list[Scheme], list[SchemeExplanation] | None]:
        """
        Executes the 3-stage matching pipeline.
        Returns (ranked match results, candidate scheme objects, optional LLM explanations).
        """
        # Multilingual Step: detect query language (override explicit language param if query is in different script)
        if query:
            detected = detect_language(query)
            if detected != "en" and language == "en":
                language = detected  # auto-detect takes precedence over default

        # Multilingual Step: translate query to English for retrieval
        english_query = query
        if query and language != "en" and self.translator:
            english_query = await self.translator.to_english(query, language)
            logger.info(f"Translated query: '{query}' → '{english_query}' (lang={language})")

        # Stage 1: SQL Filter + Rule Evaluation
        candidates = await self.sql_filter.get_candidates(self.session, profile)
        results = [self.matcher.match(s, profile) for s in candidates]

        # Stage 2: Semantic Re-ranking (if query provided)
        sorted_results = results
        if english_query:
            try:
                from app.services.embedding.embedder import GeminiEmbedder
                from app.services.embedding.retriever import SemanticRetriever
                from app.services.llm.gemini import GeminiClient

                gemini_client = GeminiClient()
                embedder = GeminiEmbedder(gemini_client)
                retriever = SemanticRetriever(self.session, embedder)
                self.semantic_reranker._retriever = retriever
                sorted_results = await self.semantic_reranker.rerank(english_query, results)
            except Exception as e:
                logger.warning(f"Semantic reranking failed due to an error: {e}. Falling back to non-semantic results.")
                sorted_results = results

        # Stage 3: LLM Re-ranking and Explanation (if enabled)
        explanations = None
        if explain and self.llm_reranker:
            # Re-rank top 15 candidates only
            top_15 = sorted_results[:15]
            llm_result = await self.llm_reranker.rerank_and_explain(
                profile, top_15, language=language
            )
            explanations = llm_result.explanations

            explanation_map = {exp.slug: exp for exp in explanations}

            def llm_sort_key(result: SchemeMatchResult) -> int:
                exp = explanation_map.get(result.slug)
                return exp.final_rank if exp else 99

            top_results = sorted(top_15, key=llm_sort_key)
            other_results = [r for r in sorted_results if r not in top_15]
            sorted_results = top_results + other_results

        if not include_ineligible:
            sorted_results = [
                r for r in sorted_results if r.status != EligibilityStatus.NOT_ELIGIBLE
            ]

        return sorted_results[:max_results], candidates, explanations

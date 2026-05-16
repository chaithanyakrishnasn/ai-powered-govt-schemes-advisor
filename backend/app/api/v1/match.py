"""API endpoints for matching."""

from __future__ import annotations

import asyncio
import json
import time
from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_matching_service
from app.core.exceptions import ProfileNotFoundError
from app.db.models import Scheme, SchemeMatch
from app.db.models import UserProfile as UserProfileORM
from app.schemas.match import (
    MatchRequest,
    MatchResponse,
    PipelineStats,
    SchemeResultItem,
)
from app.schemas.user_profile import UserProfile as UserProfileSchema
from app.services.matching.scheme_matcher import SchemeMatchResult
from app.services.matching.service import MatchingService

router = APIRouter()


@router.post("", response_model=MatchResponse)
@router.post("/", response_model=MatchResponse)
async def match_profile_endpoint(
    request: Request,
    match_request: MatchRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
    matching_service: Annotated[MatchingService, Depends(get_matching_service)],
) -> MatchResponse:
    """Run the full matching pipeline for a user profile."""
    start_time = time.monotonic()
    profile, profile_id = await _get_or_create_profile(match_request, session)

    results, candidates, explanations = await matching_service.match_profile(
        profile=profile,
        query=match_request.query,
        max_results=match_request.max_results,
        include_ineligible=match_request.include_ineligible,
        explain=match_request.explain,
        language=match_request.language,
    )

    total_latency_ms = (time.monotonic() - start_time) * 1000

    result_items = await _build_scheme_result_items(results, session)
    await _save_match_results(profile_id, result_items, session)

    stage3_tokens = None
    llm_reranker = matching_service.llm_reranker
    if explanations and llm_reranker and hasattr(llm_reranker, "output_tokens"):
        stage3_tokens = llm_reranker.output_tokens

    return MatchResponse(
        profile_id=profile_id,
        query=match_request.query,
        total_candidates=len(candidates),
        results=result_items,
        explanations=explanations,
        pipeline_stats=PipelineStats(
            stage1_candidates=len(candidates),
            stage2_reranked=bool(match_request.query),
            stage3_explained=match_request.explain,
            total_latency_ms=total_latency_ms,
            stage3_tokens=stage3_tokens,
        ),
    )


@router.get("/stream")
async def match_profile_stream(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    matching_service: Annotated[MatchingService, Depends(get_matching_service)],
    profile_id: UUID | None = None,
    query: str | None = None,
    explain: bool = False,
    language: str = "en",
) -> StreamingResponse:
    """Run the matching pipeline and stream results using SSE."""

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            if profile_id:
                profile = await session.get(UserProfileORM, profile_id)
                if not profile:
                    profile_schema = UserProfileSchema()
                else:
                    profile_schema = UserProfileSchema.model_validate(profile)
            else:
                profile_schema = UserProfileSchema()

            start_time = time.monotonic()

            # Multilingual Step: detect query language
            stream_language = language
            if query:
                from app.services.multilingual.detector import detect_language

                detected = detect_language(query)
                if detected != "en" and stream_language == "en":
                    stream_language = detected

            # Multilingual Step: translate query to English for retrieval
            english_query = query
            if query and stream_language != "en" and matching_service.translator:
                english_query = await matching_service.translator.to_english(
                    query, stream_language
                )

            candidates = await matching_service.sql_filter.get_candidates(
                session, profile_schema
            )
            stage1_results = [
                matching_service.matcher.match(s, profile_schema) for s in candidates
            ]
            stage1_items = await _build_scheme_result_items(stage1_results, session)
            stage1_payload = {
                "results": [r.model_dump(mode="json") for r in stage1_items],
                "candidate_count": len(candidates),
            }
            yield f"""event: stage1_complete
data: {json.dumps(stage1_payload)}

"""
            await asyncio.sleep(0)

            sorted_results = stage1_results
            if english_query:
                sorted_results = await matching_service.semantic_reranker.rerank(
                    english_query, stage1_results
                )
            stage2_items = await _build_scheme_result_items(sorted_results, session)
            stage2_payload = {
                "results": [r.model_dump(mode="json") for r in stage2_items]
            }
            yield f"""event: stage2_complete
data: {json.dumps(stage2_payload)}

"""
            await asyncio.sleep(0)

            if explain and matching_service.llm_reranker:
                top_15 = sorted_results[:15]
                llm_result = await matching_service.llm_reranker.rerank_and_explain(
                    profile_schema, top_15, language=stream_language
                )
                if llm_result.explanations:
                    for exp in llm_result.explanations:
                        yield f"""event: stage3_explanation
data: {json.dumps({"explanation": exp.model_dump()})}

"""
                        await asyncio.sleep(0)

            total_latency_ms = (time.monotonic() - start_time) * 1000
            yield f"""event: done
data: {json.dumps({"total_latency_ms": total_latency_ms})}

"""

        except asyncio.CancelledError:
            logger.info(f"Client disconnected from stream for profile {profile_id}")
            raise
        except Exception as e:
            logger.error(
                f"Error during match stream for profile {profile_id}: {e}",
                exc_info=True,
            )
            error_payload = {"message": "An internal error occurred", "stage": "stream"}
            yield f"""event: error
data: {json.dumps(error_payload)}

"""

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def _get_or_create_profile(
    match_request: MatchRequest, session: AsyncSession
) -> tuple[UserProfileSchema, UUID]:
    if match_request.profile_id:
        profile = await session.get(UserProfileORM, match_request.profile_id)
        if not profile:
            raise ProfileNotFoundError(profile_id=match_request.profile_id)
        return UserProfileSchema.model_validate(profile), match_request.profile_id

    if match_request.profile:
        profile_data = match_request.profile.model_dump(exclude_unset=True)
        new_profile = UserProfileORM(**profile_data)
        session.add(new_profile)
        await session.commit()
        await session.refresh(new_profile)
        return UserProfileSchema.model_validate(new_profile), new_profile.id

    raise ValueError("Either profile_id or profile must be provided.")


async def _build_scheme_result_items(
    results: list[SchemeMatchResult], session: AsyncSession
) -> list[SchemeResultItem]:
    scheme_ids = [result.scheme_id for result in results]
    schemes_by_id: dict[int, Scheme] = {}
    if scheme_ids:
        schemes_meta = await session.execute(
            select(Scheme).where(Scheme.id.in_(scheme_ids))
        )
        schemes_by_id = {scheme.id: scheme for scheme in schemes_meta.scalars().all()}

    items: list[SchemeResultItem] = []
    for result in results:
        scheme = schemes_by_id.get(result.scheme_id)
        items.append(
            SchemeResultItem(
                scheme_id=result.scheme_id,
                slug=result.slug,
                name=result.name,
                status=result.status,
                score=result.score,
                semantic_similarity=result.semantic_similarity,
                combined_score=result.combined_score,
                level=scheme.level if scheme else "unknown",
                state=scheme.state if scheme else None,
                categories=scheme.categories if scheme else [],
                benefit_type=scheme.benefit_type if scheme else None,
                benefit_description=scheme.benefit_description if scheme else None,
                application_url=scheme.application_url if scheme else None,
                missing_fields=result.missing_fields,
            )
        )
    return items


async def _save_match_results(
    profile_id: UUID, results: list[SchemeResultItem], db: AsyncSession
) -> None:
    logger.info(f"Saving {len(results)} match results for profile {profile_id}")
    try:
        for result in results[:10]:
            if result.level == "unknown":
                continue
            match = SchemeMatch(
                user_id=profile_id,
                scheme_id=result.scheme_id,
                match_score=result.score,
                eligibility_status=result.status.value,
            )
            await db.merge(match)
        await db.commit()
        logger.info(f"Successfully saved match results for profile {profile_id}")
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to save match results for profile {profile_id}: {e}")

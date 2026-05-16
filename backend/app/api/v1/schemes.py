"""API endpoints for schemes."""

from __future__ import annotations

import math
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_db
from app.core.exceptions import SchemeNotFoundError
from app.db.models import Scheme
from app.schemas.scheme import PaginatedSchemes, SchemeDetailResponse, SchemeListItem

router = APIRouter()


@router.get("", response_model=PaginatedSchemes)
@router.get("/", response_model=PaginatedSchemes)
async def list_schemes(
    session: Annotated[AsyncSession, Depends(get_db)],
    q: str | None = None,
    level: str | None = None,
    state: str | None = None,
    category: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=50),
) -> PaginatedSchemes:
    """List schemes with optional filters and pagination."""
    query = select(Scheme)
    if q:
        query = query.where(Scheme.search_text.match(q, postgresql_regconfig="english"))
    if level:
        query = query.where(Scheme.level == level)
    if state:
        query = query.where(Scheme.state == state)
    if category:
        query = query.where(Scheme.categories.contains([category]))

    # Get total count before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query) or 0

    # Apply pagination
    query = query.offset((page - 1) * size).limit(size)
    result = await session.execute(query)
    items = [SchemeListItem.model_validate(s) for s in result.scalars().all()]

    return PaginatedSchemes(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size) if total > 0 else 0,
    )


@router.get("/{slug}", response_model=SchemeDetailResponse)
async def get_scheme_details(
    slug: str, session: Annotated[AsyncSession, Depends(get_db)]
) -> SchemeDetailResponse:
    """Retrieve full details for a single scheme by its slug."""
    query = (
        select(Scheme)
        .options(selectinload(Scheme.eligibility_rules))
        .where(Scheme.slug == slug)
    )
    result = await session.execute(query)
    scheme = result.scalar_one_or_none()

    if not scheme:
        raise SchemeNotFoundError(slug=slug)

    return SchemeDetailResponse.model_validate(scheme)

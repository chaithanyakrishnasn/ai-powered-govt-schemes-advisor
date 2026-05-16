"""API endpoints for user profiles."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.exceptions import ProfileNotFoundError
from app.db.models import UserProfile as UserProfileORM
from app.schemas.profile import ProfileResponse, UserProfileCreate
from app.schemas.user_profile import UserProfile as UserProfileSchema

router = APIRouter()


@router.post("", status_code=201, response_model=ProfileResponse)
@router.post("/", status_code=201, response_model=ProfileResponse)
async def create_user_profile(
    profile_data: UserProfileCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileResponse:
    """Create a new user profile."""
    profile_dict = profile_data.model_dump(exclude_unset=True)
    new_profile = UserProfileORM(**profile_dict)
    session.add(new_profile)
    await session.commit()
    await session.refresh(new_profile)

    return ProfileResponse(
        profile_id=new_profile.id,
        created_at=new_profile.created_at,
        field_count=len(profile_dict),
    )


@router.get("/{profile_id}", response_model=UserProfileSchema)
async def get_user_profile(
    profile_id: UUID, session: Annotated[AsyncSession, Depends(get_db)]
) -> UserProfileORM:
    """Retrieve a user profile by its ID."""
    profile = await session.get(UserProfileORM, profile_id)
    if not profile:
        raise ProfileNotFoundError(profile_id=profile_id)
    return profile


@router.patch("/{profile_id}", response_model=UserProfileSchema)
async def update_user_profile(
    profile_id: UUID,
    profile_data: UserProfileCreate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> UserProfileORM:
    """Update a user profile."""
    profile = await session.get(UserProfileORM, profile_id)
    if not profile:
        raise ProfileNotFoundError(profile_id=profile_id)

    update_data = profile_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(profile, field, value)

    await session.commit()
    await session.refresh(profile)
    return profile

"""Pydantic schemas for user profiles."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.schemas.user_profile import UserProfile


class UserProfileCreate(UserProfile):
    """
    Schema for creating a user profile.
    All fields are optional, inheriting from the base UserProfile schema.
    """

    pass


class ProfileResponse(BaseModel):
    """
    Response schema for profile creation.
    """

    model_config = ConfigDict(from_attributes=True)

    profile_id: UUID
    created_at: datetime
    field_count: int

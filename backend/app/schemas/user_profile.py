from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class UserProfile(BaseModel):
    """
    Pydantic model for user profile data used in matching.
    All fields are optional to allow for progressive data collection.
    """

    id: UUID | None = None
    age: int | None = None
    gender: Literal["male", "female", "other", "prefer_not_to_say"] | None = None
    state: str | None = None  # Full name, e.g., "Karnataka"
    district: str | None = None
    annual_income: float | None = None  # In INR
    occupation: str | None = None
    employment_status: (
        Literal["employed", "unemployed", "self_employed", "student", "retired"] | None
    ) = None
    caste_category: Literal["GEN", "OBC", "SC", "ST", "EWS"] | None = None
    religion: str | None = None
    marital_status: Literal["single", "married", "widowed", "divorced"] | None = None
    is_farmer: bool | None = None
    land_holding_acres: float | None = None
    education_level: (
        Literal[
            "none",
            "primary",
            "secondary",
            "higher_secondary",
            "diploma",
            "graduate",
            "postgraduate",
            "masters_degree",
            "phd",
        ]
        | None
    ) = None
    family_size: int | None = None
    has_disability: bool | None = None
    disability_percentage: int | None = None

    model_config = ConfigDict(extra="forbid", from_attributes=True)

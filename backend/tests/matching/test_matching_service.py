import json
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EligibilityRule, Scheme
from app.schemas.user_profile import UserProfile
from app.services.matching.service import MatchingService

PROFILE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "test_profiles"


@pytest.mark.asyncio
async def test_matching_service_farmer(db_session: AsyncSession) -> None:
    # Setup: Add a farmer-specific scheme
    farmer_scheme = Scheme(
        id=100,
        slug="farmer-scheme",
        name="Farmer Scheme",
        level="state",
        state="Karnataka",
        eligibility_rules=[
            EligibilityRule(
                rule_type="is_farmer", operator="eq", value={"value": True}
            ),
            EligibilityRule(
                rule_type="land_holding_acres", operator="lte", value={"value": 5}
            ),
        ],
        source_url="test",
        source="test",
    )
    db_session.add(farmer_scheme)
    await db_session.commit()

    profile_path = PROFILE_DIR / "farmer_karnataka.json"
    with profile_path.open() as f:
        profile_data = json.load(f)
    profile = UserProfile(**profile_data)

    service = MatchingService(db_session)
    results, _, _ = await service.match_profile(profile)

    assert len(results) > 0
    assert any(r.slug == "farmer-scheme" for r in results)
    top_result = results[0]
    assert top_result.status in ("eligible", "likely_eligible")


@pytest.mark.asyncio
async def test_matching_service_student(db_session: AsyncSession) -> None:
    # Setup: Add a scholarship scheme
    student_scheme = Scheme(
        id=101,
        slug="student-scheme",
        name="Scholarship for SC Students",
        level="state",
        state="Karnataka",
        eligibility_rules=[
            EligibilityRule(
                rule_type="caste_category", operator="eq", value={"value": "SC"}
            ),
            EligibilityRule(
                rule_type="education_level", operator="gte", value={"value": "graduate"}
            ),
        ],
        source_url="test",
        source="test",
    )
    db_session.add(student_scheme)
    await db_session.commit()

    profile_path = PROFILE_DIR / "student_sc.json"
    with profile_path.open() as f:
        profile_data = json.load(f)
    profile = UserProfile(**profile_data)

    service = MatchingService(db_session)
    results, _, _ = await service.match_profile(profile, max_results=10)

    assert len(results) > 0
    assert any(r.slug == "student-scheme" for r in results)

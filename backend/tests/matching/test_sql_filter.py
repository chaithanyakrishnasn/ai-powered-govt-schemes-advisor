import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EligibilityRule, Scheme
from app.schemas.user_profile import UserProfile
from app.services.matching.sql_filter import SQLEligibilityFilter


@pytest.mark.asyncio
async def test_sql_filter_state(db_session: AsyncSession) -> None:
    # Setup
    scheme1 = Scheme(
        id=1,
        slug="s1",
        name="KA Only",
        level="state",
        state="Karnataka",
        source_url="test",
        source="test",
    )
    scheme2 = Scheme(
        id=2,
        slug="s2",
        name="Central",
        level="central",
        source_url="test",
        source="test",
    )
    db_session.add_all([scheme1, scheme2])
    await db_session.commit()

    profile = UserProfile(state="Karnataka")
    candidates = await SQLEligibilityFilter.get_candidates(db_session, profile)
    assert len(candidates) >= 2

    profile = UserProfile(state="Maharashtra")
    candidates = await SQLEligibilityFilter.get_candidates(db_session, profile)
    assert len(candidates) >= 1
    assert not any(c.slug == "s1" for c in candidates)
    assert any(c.slug == "s2" for c in candidates)


@pytest.mark.asyncio
async def test_sql_filter_no_false_negatives(db_session: AsyncSession) -> None:
    # Setup
    scheme1 = Scheme(
        id=3,
        slug="s3",
        name="Age 20-30",
        level="central",
        eligibility_rules=[
            EligibilityRule(
                rule_type="age", operator="between", value={"min": 20, "max": 30}
            )
        ],
        source_url="test",
        source="test",
    )
    db_session.add(scheme1)
    await db_session.commit()

    profile = UserProfile(age=25)
    candidates = await SQLEligibilityFilter.get_candidates(db_session, profile)
    assert any(c.slug == "s3" for c in candidates)

    profile = UserProfile(age=35)
    candidates = await SQLEligibilityFilter.get_candidates(db_session, profile)
    assert not any(c.slug == "s3" for c in candidates)

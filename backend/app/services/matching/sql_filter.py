from __future__ import annotations

from loguru import logger
from sqlalchemy import Integer, and_, func, not_, or_, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import EligibilityRule, Scheme
from app.schemas.user_profile import UserProfile


class SQLEligibilityFilter:

    @staticmethod
    async def get_candidates(session: AsyncSession, profile: UserProfile) -> list[Scheme]:
        """
        Pre-filters schemes in SQL to produce a candidate set.
        This query is designed to avoid false negatives at all costs,
        while reducing the number of schemes that need to be evaluated in Python.
        """
        query = select(Scheme)
        
        async with session.begin_nested() if session.in_transaction() else session.begin():
            total_schemes_count = await session.scalar(select(func.count(Scheme.id)))
            logger.info(f"Initial scheme count: {total_schemes_count}")

        # State filter
        if profile.state:
            query = query.where(
                or_(
                    Scheme.level != 'state',
                    Scheme.state.is_(None),
                    func.lower(Scheme.state) == func.lower(profile.state)
                )
            )
        
        # Gender filter
        if profile.gender:
            gender_rule_subquery = select(EligibilityRule.scheme_id).where(
                and_(
                    EligibilityRule.rule_type == 'gender',
                    EligibilityRule.value.cast(JSONB)['value'].as_string() != profile.gender
                )
            ).distinct()
            query = query.where(not_(Scheme.id.in_(gender_rule_subquery)))
        
        # Age filter
        if profile.age:
            age_rule_subquery = select(EligibilityRule.scheme_id).where(
                and_(
                    EligibilityRule.rule_type == 'age',
                    EligibilityRule.operator == 'between',
                    or_(
                        EligibilityRule.value.cast(JSONB)['min'].as_float().cast(Integer) > profile.age,
                        EligibilityRule.value.cast(JSONB)['max'].as_float().cast(Integer) < profile.age
                    )
                )
            ).distinct()
            query = query.where(not_(Scheme.id.in_(age_rule_subquery)))

        # Income filter
        if profile.annual_income:
            income_rule_subquery = select(EligibilityRule.scheme_id).where(
                and_(
                    EligibilityRule.rule_type == 'income',
                    EligibilityRule.operator == 'lte',
                    EligibilityRule.value.cast(JSONB)['value'].as_float() < profile.annual_income
                )
            ).distinct()
            query = query.where(not_(Scheme.id.in_(income_rule_subquery)))

        # Eager load rules to avoid N+1 queries later
        query = query.options(selectinload(Scheme.eligibility_rules))
        
        result = await session.execute(query)
        candidates = result.scalars().unique().all()

        logger.info(f"Final candidate count: {len(candidates)}")
        return list(candidates)

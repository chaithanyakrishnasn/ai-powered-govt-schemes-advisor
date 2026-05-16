from __future__ import annotations

from dataclasses import dataclass

from loguru import logger
from sqlalchemy import delete, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EligibilityRule as DBEligibilityRule
from app.db.models import Scheme as DBScheme


@dataclass
class UpsertResult:
    slug: str
    action: str  # "inserted" | "updated" | "failed"
    rules_count: int = 0
    error: str | None = None


class SchemeUpserter:
    """Idempotent scheme + rules writer.

    Each call to ``upsert`` runs in its own transaction. A failure in one
    scheme never rolls back another.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        scheme: DBScheme,
        rules: list[DBEligibilityRule],
    ) -> UpsertResult:
        try:
            async with self._session.begin():
                scheme_id, action = await self._upsert_scheme(scheme)
                await self._replace_rules(scheme_id, rules)
            return UpsertResult(slug=scheme.slug, action=action, rules_count=len(rules))
        except Exception as exc:
            err = str(exc)
            logger.error(f"Upsert failed for {scheme.slug!r}: {err}")
            return UpsertResult(slug=scheme.slug, action="failed", error=err)

    async def _upsert_scheme(self, scheme: DBScheme) -> tuple[int, str]:
        """Insert or update the scheme row. Returns (scheme_id, action)."""
        values: dict[str, object] = {
            "slug": scheme.slug,
            "name": scheme.name,
            "description": scheme.description,
            "ministry": scheme.ministry,
            "level": scheme.level,
            "state": scheme.state,
            "categories": scheme.categories,
            "benefit_type": scheme.benefit_type,
            "benefit_amount_min": scheme.benefit_amount_min,
            "benefit_amount_max": scheme.benefit_amount_max,
            "benefit_description": scheme.benefit_description,
            "application_url": scheme.application_url,
            "application_mode": scheme.application_mode,
            "documents_required": scheme.documents_required,
            "raw_eligibility_text": scheme.raw_eligibility_text,
            "search_text": scheme.search_text,
            "source_url": scheme.source_url,
            "source": scheme.source,
            "last_scraped_at": scheme.last_scraped_at,
            "updated_at": scheme.updated_at,
            "is_active": True,
        }

        # ON CONFLICT (slug) DO UPDATE — xmax trick distinguishes insert vs update.
        # xmax == 0 → new row inserted; xmax > 0 → existing row updated.
        stmt = (
            pg_insert(DBScheme)
            .values(**values)
            .on_conflict_do_update(
                index_elements=["slug"],
                set_={k: v for k, v in values.items() if k != "slug"},
            )
            .returning(DBScheme.id, text("xmax"))
        )

        row = (await self._session.execute(stmt)).one()
        scheme_id: int = row[0]
        xmax: int = row[1]
        action = "inserted" if xmax == 0 else "updated"
        return scheme_id, action

    async def _replace_rules(
        self, scheme_id: int, rules: list[DBEligibilityRule]
    ) -> None:
        """Delete existing rules for this scheme, then insert the new set."""
        await self._session.execute(
            delete(DBEligibilityRule).where(DBEligibilityRule.scheme_id == scheme_id)
        )
        for rule in rules:
            rule.scheme_id = scheme_id
            self._session.add(rule)

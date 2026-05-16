from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EligibilityRule as DBEligibilityRule
from app.db.models import Scheme as DBScheme
from app.services.embedding.embedder import EmbedTaskType, GeminiEmbedder
from app.services.extraction.schemas import EligibilityRule
from app.services.ingestion.eligibility_summary import summarize_rules

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import async_sessionmaker


@dataclass
class PopulationReport:
    total_embedded: int = 0
    skipped: int = 0
    failed: int = 0
    truncated: int = 0
    elapsed_seconds: float = 0.0
    estimated_cost_usd: float = 0.0
    scheme_count: int = 0
    force: bool = False


def _build_search_text_from_db(
    name: str,
    description: str | None,
    benefit_description: str | None,
    categories: list[str],
    rules: list[EligibilityRule],
) -> str:
    parts: list[str] = [name]
    if description:
        parts.append(description)
    if benefit_description:
        parts.append(benefit_description)
    if categories:
        parts.append(f"Categories: {', '.join(categories)}")
    summary = summarize_rules(rules)
    if summary:
        parts.append(f"Eligible for: {summary}")
    return "\n\n".join(parts)


class EmbeddingPopulator:
    def __init__(
        self,
        session_maker: async_sessionmaker[AsyncSession],
        embedder: GeminiEmbedder,
    ) -> None:
        self._session_maker = session_maker
        self._embedder = embedder

    async def refresh_search_text(self, batch_size: int = 100) -> dict[str, object]:
        """Re-compute search_text for all schemes using current rules + eligibility summary."""
        start = time.monotonic()
        updated = 0
        total_before = total_after = 0

        async with self._session_maker() as session:
            # Load all schemes
            schemes_result = await session.execute(
                select(
                    DBScheme.id,
                    DBScheme.name,
                    DBScheme.description,
                    DBScheme.benefit_description,
                    DBScheme.categories,
                    DBScheme.search_text,
                )
            )
            schemes = schemes_result.fetchall()

            # Load all rules grouped by scheme_id
            rules_result = await session.execute(
                select(
                    DBEligibilityRule.scheme_id,
                    DBEligibilityRule.rule_type,
                    DBEligibilityRule.operator,
                    DBEligibilityRule.value,
                    DBEligibilityRule.logic_group,
                    DBEligibilityRule.group_operator,
                    DBEligibilityRule.is_required,
                    DBEligibilityRule.description,
                    DBEligibilityRule.confidence,
                )
            )
            raw_rules = rules_result.fetchall()

        # Group DB rules into EligibilityRule objects by scheme_id
        from app.services.extraction.schemas import RuleValue

        rules_by_scheme: dict[int, list[EligibilityRule]] = {}
        for row in raw_rules:
            val_dict = row.value if isinstance(row.value, dict) else {}
            rv = RuleValue(
                value=val_dict.get("value"),
                min=val_dict.get("min"),
                max=val_dict.get("max"),
                **{"in": val_dict.get("in")},
            )
            try:
                rule = EligibilityRule(
                    rule_type=row.rule_type,
                    operator=row.operator,
                    value=rv,
                    logic_group=row.logic_group,
                    group_operator=row.group_operator,
                    is_required=row.is_required,
                    description=row.description or "",
                    confidence=float(row.confidence or 0),
                )
                rules_by_scheme.setdefault(row.scheme_id, []).append(rule)
            except Exception:
                pass  # skip invalid rules

        # Re-compute and batch-update
        updates: list[dict[str, object]] = []
        for row in schemes:
            old_text = row.search_text or ""
            total_before += len(old_text)

            new_text = _build_search_text_from_db(
                name=row.name,
                description=row.description,
                benefit_description=row.benefit_description,
                categories=list(row.categories or []),
                rules=rules_by_scheme.get(row.id, []),
            )
            total_after += len(new_text)
            updates.append({"_id": row.id, "search_text": new_text})

        # Apply in batches
        for i in range(0, len(updates), batch_size):
            chunk = updates[i : i + batch_size]
            async with self._session_maker() as session, session.begin():
                for entry in chunk:
                    await session.execute(
                        update(DBScheme)
                        .where(DBScheme.id == entry["_id"])
                        .values(search_text=entry["search_text"])
                    )
                    updated += 1
            logger.info(f"search_text refresh: {min(i + batch_size, len(updates))}/{len(updates)}")

        elapsed = time.monotonic() - start
        avg_before = total_before / max(1, len(schemes))
        avg_after = total_after / max(1, len(schemes))
        logger.info(
            f"Refreshed search_text for {updated} schemes in {elapsed:.1f}s | "
            f"avg length: {avg_before:.0f} → {avg_after:.0f} chars"
        )
        return {
            "updated": updated,
            "avg_before": avg_before,
            "avg_after": avg_after,
            "elapsed_seconds": elapsed,
        }

    async def populate(
        self,
        *,
        force: bool = False,
        batch_size: int = 100,
        only_missing: bool = True,
    ) -> PopulationReport:
        """Embed all schemes and write vectors to DB.

        By default embeds only rows where embedding IS NULL (idempotent).
        Pass force=True to re-embed everything.
        """
        start = time.monotonic()
        report = PopulationReport(force=force)

        async with self._session_maker() as session:
            if force or not only_missing:
                result = await session.execute(
                    select(DBScheme.id, DBScheme.search_text)
                )
            else:
                result = await session.execute(
                    select(DBScheme.id, DBScheme.search_text).where(
                        DBScheme.embedding.is_(None)
                    )
                )
            rows = result.fetchall()

        report.scheme_count = len(rows)
        if not rows:
            logger.info("0 schemes need embedding — already complete.")
            report.elapsed_seconds = time.monotonic() - start
            return report

        texts = [row.search_text or "" for row in rows]
        ids = [row.id for row in rows]

        report.estimated_cost_usd = GeminiEmbedder.estimate_cost(texts)
        print(
            f"\n── Embedding preflight ──────────────────────────────\n"
            f"  Schemes to embed  : {len(rows)}\n"
            f"  Est. cost         : ${report.estimated_cost_usd:.4f} USD\n"
            f"────────────────────────────────────────────────────\n"
        )

        # Embed in batches
        embeddings = await self._embedder.embed_batch(
            texts,
            task_type=EmbedTaskType.RETRIEVAL_DOCUMENT,
            batch_size=batch_size,
        )
        report.truncated = self._embedder.truncation_count

        # Write back in batches of 100
        for i in range(0, len(ids), batch_size):
            chunk_ids = ids[i : i + batch_size]
            chunk_vecs = embeddings[i : i + batch_size]

            async with self._session_maker() as session, session.begin():
                for scheme_id, vec in zip(chunk_ids, chunk_vecs, strict=True):
                    is_zero = all(v == 0.0 for v in vec)
                    if is_zero:
                        report.failed += 1
                        logger.warning(
                            f"Scheme id={scheme_id} has zero embedding (API error) — skipping"
                        )
                        continue
                    await session.execute(
                        update(DBScheme)
                        .where(DBScheme.id == scheme_id)
                        .values(embedding=vec)
                    )
                    report.total_embedded += 1

            done = min(i + batch_size, len(ids))
            if done % (batch_size * 2) == 0 or done == len(ids):
                logger.info(
                    f"Embedding progress: {done}/{len(ids)} | "
                    f"embedded={report.total_embedded} failed={report.failed}"
                )

        report.elapsed_seconds = time.monotonic() - start
        return report

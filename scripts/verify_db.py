"""Quick smoke-test: insert one fake scheme + eligibility rule + translation, read them back, rollback."""

import argparse
import asyncio
import sys
from pathlib import Path

# Allow running from repo root without installing the package
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.models import EligibilityRule, Scheme, SchemeTranslation


async def run(keep: bool) -> None:
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with session_maker() as session:
        async with session.begin():
            # Insert a fake scheme
            scheme = Scheme(
                slug="pm-kisan-test",
                name="PM-KISAN (Test)",
                description="Income support for small and marginal farmers.",
                level="central",
                ministry="Ministry of Agriculture",
                categories=["agriculture", "subsidy"],
                benefit_type="cash",
                benefit_amount_min=6000,
                benefit_amount_max=6000,
                benefit_description="₹6,000/year in three installments",
                source_url="https://pmkisan.gov.in",
                source="myscheme",
                search_text="PM-KISAN income support farmer agriculture subsidy cash",
            )
            session.add(scheme)
            await session.flush()  # get scheme.id

            rule = EligibilityRule(
                scheme_id=scheme.id,
                rule_type="occupation",
                operator="eq",
                value={"value": "farmer"},
                description="Applicant must be a farmer",
                confidence=0.95,
            )
            session.add(rule)

            translation = SchemeTranslation(
                scheme_id=scheme.id,
                language="hi",
                name="प्रधानमंत्री किसान सम्मान निधि",
                description="छोटे और सीमांत किसानों के लिए आय सहायता।",
                benefit_description="₹6,000 प्रति वर्ष",
            )
            session.add(translation)
            await session.flush()

            # Read back via ORM
            stmt = (
                select(Scheme)
                .where(Scheme.slug == "pm-kisan-test")
            )
            result = await session.execute(stmt)
            fetched: Scheme = result.scalars().one()

            rule_stmt = select(EligibilityRule).where(
                EligibilityRule.scheme_id == fetched.id
            )
            rules = (await session.execute(rule_stmt)).scalars().all()

            trans_stmt = select(SchemeTranslation).where(
                SchemeTranslation.scheme_id == fetched.id
            )
            translations = (await session.execute(trans_stmt)).scalars().all()

            print("\n=== verify_db.py results ===")
            print(f"Scheme:      {fetched!r}")
            print(f"  id={fetched.id}  slug={fetched.slug!r}  level={fetched.level!r}")
            print(f"  categories={fetched.categories}  benefit_type={fetched.benefit_type!r}")
            print(f"  embedding column present: {fetched.embedding is None!r} (None = not yet embedded)")
            print(f"Rules:       {len(rules)} rule(s)")
            for r in rules:
                print(f"  {r!r}  value={r.value}  confidence={r.confidence}")
            print(f"Translations:{len(translations)} translation(s)")
            for t in translations:
                print(f"  {t!r}  name={t.name!r}")
            print("=== All assertions passed ===\n")

            assert fetched.slug == "pm-kisan-test"
            assert fetched.level == "central"
            assert "agriculture" in fetched.categories
            assert len(rules) == 1
            assert rules[0].value == {"value": "farmer"}
            assert len(translations) == 1
            assert translations[0].language == "hi"

            if keep:
                print("--keep flag set: committing rows (skipping rollback)")
            else:
                raise _Rollback("rolling back test data")

    await engine.dispose()


class _Rollback(Exception):
    pass


async def main(keep: bool) -> None:
    try:
        await run(keep)
    except _Rollback as e:
        print(f"Rolled back: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify DB schema with a smoke-test insert.")
    parser.add_argument("--keep", action="store_true", help="Commit rows instead of rolling back")
    args = parser.parse_args()
    asyncio.run(main(args.keep))

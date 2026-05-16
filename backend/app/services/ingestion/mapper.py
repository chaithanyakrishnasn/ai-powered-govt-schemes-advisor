from __future__ import annotations

import re
from datetime import UTC, datetime
from decimal import Decimal

from app.db.models import EligibilityRule as DBEligibilityRule
from app.db.models import Scheme as DBScheme
from app.schemas.raw_scheme import RawScheme
from app.services.extraction.schemas import EligibilityRule, ExtractionResult
from app.services.ingestion.eligibility_summary import summarize_rules

_LAKH = 100_000

# Ordered from most-specific to least; first match wins per occurrence.
_AMOUNT_PATTERNS = [
    # "₹6,000" / "Rs. 6,000" / "Rs 6000" — with optional lakh suffix
    r"(?:₹|Rs\.?\s*)(\d[\d,]*)(?:\s*(?:lakh|lac|lacs|lakhs))?",
    # "6000 rupees" / "6,000 rupees"
    r"(\d[\d,]*)\s*rupees?",
]


def _parse_amounts(text: str | None) -> tuple[Decimal | None, Decimal | None]:
    """Return (min, max) benefit amounts parsed from free text. Best-effort only."""
    if not text:
        return None, None

    amounts: list[float] = []
    for pat in _AMOUNT_PATTERNS:
        for m in re.finditer(pat, text, re.IGNORECASE):
            raw = m.group(1).replace(",", "")
            try:
                n = float(raw)
            except ValueError:
                continue
            full = m.group(0)
            if re.search(r"\blakh|lac\b", full, re.IGNORECASE):
                n *= _LAKH
            amounts.append(n)

    if not amounts:
        return None, None
    lo, hi = min(amounts), max(amounts)
    if lo == hi:
        return Decimal(str(lo)), None
    return Decimal(str(lo)), Decimal(str(hi))


def _normalize_categories(cats: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for c in cats:
        normed = c.strip().lower()
        if normed and normed not in seen:
            seen.add(normed)
            result.append(normed)
    return result


def _build_search_text(
    raw: RawScheme, rules: list[EligibilityRule] | None = None
) -> str:
    parts: list[str] = [raw.name]
    if raw.description:
        parts.append(raw.description)
    if raw.benefit_description:
        parts.append(raw.benefit_description)
    if raw.categories:
        parts.append(f"Categories: {', '.join(raw.categories)}")
    if rules:
        summary = summarize_rules(rules)
        if summary:
            parts.append(f"Eligible for: {summary}")
    return "\n\n".join(parts)


def to_db_objects(
    raw: RawScheme,
    extraction: ExtractionResult,
) -> tuple[DBScheme, list[DBEligibilityRule]]:
    """Map a RawScheme + ExtractionResult into DB-ready ORM objects.

    The returned DBScheme has no ``id`` set — that is assigned by the DB.
    EligibilityRule objects have no ``scheme_id`` — set this after the parent insert.
    """
    now = datetime.now(UTC)
    benefit_min, benefit_max = _parse_amounts(raw.benefit_description)

    scheme = DBScheme(
        slug=raw.slug,
        name=raw.name,
        description=raw.description,
        ministry=raw.ministry,
        level=raw.level,
        state=raw.state,
        categories=_normalize_categories(raw.categories),
        benefit_type=raw.benefit_type,
        benefit_amount_min=benefit_min,
        benefit_amount_max=benefit_max,
        benefit_description=raw.benefit_description,
        application_url=raw.application_url,
        application_mode=raw.application_mode,
        documents_required=raw.documents_required,
        raw_eligibility_text=raw.raw_eligibility_text,
        search_text=_build_search_text(raw, extraction.rules),
        source_url=raw.source_url,
        source=raw.source,
        last_scraped_at=now,
        updated_at=now,
    )

    rules: list[DBEligibilityRule] = [
        DBEligibilityRule(
            rule_type=r.rule_type,
            operator=r.operator,
            value=r.value.model_dump(by_alias=True),
            logic_group=r.logic_group,
            group_operator=r.group_operator,
            is_required=r.is_required,
            description=r.description,
            confidence=Decimal(str(r.confidence)),
        )
        for r in extraction.rules
    ]

    return scheme, rules

"""Unit tests for mapper — no DB, no network."""

from __future__ import annotations

from decimal import Decimal

from app.schemas.raw_scheme import RawScheme
from app.services.extraction.schemas import EligibilityRule, ExtractionResult, RuleValue
from app.services.ingestion.mapper import _normalize_categories, _parse_amounts, to_db_objects


def _raw(**kwargs: object) -> RawScheme:
    defaults: dict[str, object] = {
        "slug": "test-scheme",
        "name": "Test Scheme",
        "level": "central",
        "source_url": "https://example.com",
        "source": "myscheme",
    }
    defaults.update(kwargs)
    return RawScheme.model_validate(defaults)


def _extraction(rules: list[EligibilityRule] | None = None) -> ExtractionResult:
    return ExtractionResult(rules=rules or [], overall_confidence=0.9)


# ── _parse_amounts ────────────────────────────────────────────────────────────

class TestParseAmounts:
    def test_none_input(self) -> None:
        assert _parse_amounts(None) == (None, None)

    def test_empty_string(self) -> None:
        assert _parse_amounts("") == (None, None)

    def test_no_currency(self) -> None:
        assert _parse_amounts("Cash benefit for farmers") == (None, None)

    def test_rupee_symbol(self) -> None:
        lo, hi = _parse_amounts("Get ₹6000 per year")
        assert lo == Decimal("6000")
        assert hi is None

    def test_rs_prefix(self) -> None:
        lo, hi = _parse_amounts("Rs. 3,000 monthly assistance")
        assert lo == Decimal("3000")

    def test_lakh_multiplier(self) -> None:
        lo, hi = _parse_amounts("Up to ₹2 lakh loan")
        assert lo == Decimal("200000")

    def test_range_two_amounts(self) -> None:
        lo, hi = _parse_amounts("₹2000 to ₹5000 per month")
        assert lo == Decimal("2000")
        assert hi == Decimal("5000")

    def test_commas_in_number(self) -> None:
        lo, _ = _parse_amounts("₹1,50,000 grant")
        assert lo == Decimal("150000")


# ── _normalize_categories ─────────────────────────────────────────────────────

class TestNormalizeCategories:
    def test_lowercases(self) -> None:
        assert _normalize_categories(["Agriculture", "Health"]) == ["agriculture", "health"]

    def test_dedupes(self) -> None:
        assert _normalize_categories(["SC/ST", "SC/ST"]) == ["sc/st"]

    def test_strips_whitespace(self) -> None:
        assert _normalize_categories(["  Women  "]) == ["women"]

    def test_empty_list(self) -> None:
        assert _normalize_categories([]) == []

    def test_empty_string_filtered(self) -> None:
        assert _normalize_categories([""]) == []


# ── to_db_objects ─────────────────────────────────────────────────────────────

class TestToDbObjects:
    def test_basic_mapping(self) -> None:
        raw = _raw(name="PM Kisan", ministry="Agriculture", level="central")
        scheme, rules = to_db_objects(raw, _extraction())
        assert scheme.slug == "test-scheme"
        assert scheme.name == "PM Kisan"
        assert scheme.ministry == "Agriculture"
        assert scheme.level == "central"
        assert rules == []

    def test_categories_normalized(self) -> None:
        raw = _raw(categories=["Farmers", "farmers", "AGRICULTURE"])
        scheme, _ = to_db_objects(raw, _extraction())
        assert scheme.categories == ["farmers", "agriculture"]

    def test_search_text_includes_name(self) -> None:
        raw = _raw(name="My Scheme", description="A great scheme")
        scheme, _ = to_db_objects(raw, _extraction())
        assert "My Scheme" in (scheme.search_text or "")
        assert "A great scheme" in (scheme.search_text or "")

    def test_benefit_amount_parsed(self) -> None:
        raw = _raw(benefit_description="Provides ₹6000 per year to beneficiaries")
        scheme, _ = to_db_objects(raw, _extraction())
        assert scheme.benefit_amount_min == Decimal("6000")

    def test_rules_mapped(self) -> None:
        rule = EligibilityRule(
            rule_type="age",
            operator="between",
            value=RuleValue(min=18.0, max=60.0),
            description="Age between 18 and 60",
            confidence=0.9,
        )
        _, rules = to_db_objects(_raw(), _extraction([rule]))
        assert len(rules) == 1
        db_rule = rules[0]
        assert db_rule.rule_type == "age"
        assert db_rule.operator == "between"
        assert db_rule.value == {"value": None, "min": 18.0, "max": 60.0, "in": None}
        assert db_rule.confidence == Decimal("0.9")

    def test_rule_confidence_decimal(self) -> None:
        rule = EligibilityRule(
            rule_type="income",
            operator="lte",
            value=RuleValue(value=300000),
            description="Income at most 3 lakh",
            confidence=0.95,
        )
        _, rules = to_db_objects(_raw(), _extraction([rule]))
        assert rules[0].confidence == Decimal("0.95")

    def test_state_scheme(self) -> None:
        raw = _raw(level="state", state="Karnataka")
        scheme, _ = to_db_objects(raw, _extraction())
        assert scheme.level == "state"
        assert scheme.state == "Karnataka"

    def test_no_id_on_scheme(self) -> None:
        scheme, _ = to_db_objects(_raw(), _extraction())
        # Before DB insert, SQLAlchemy leaves the PK as None
        assert scheme.id is None

    def test_no_scheme_id_on_rules(self) -> None:
        rule = EligibilityRule(
            rule_type="gender",
            operator="eq",
            value=RuleValue(value="female"),
            description="Female applicants",
            confidence=0.85,
        )
        _, rules = to_db_objects(_raw(), _extraction([rule]))
        # scheme_id is not set by mapper; upserter sets it after parent insert
        assert rules[0].scheme_id is None  # type: ignore[union-attr]

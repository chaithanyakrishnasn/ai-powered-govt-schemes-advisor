"""Unit tests for the deterministic eligibility rule summarizer."""

from __future__ import annotations

from app.services.extraction.schemas import EligibilityRule, RuleValue
from app.services.ingestion.eligibility_summary import summarize_rules


def _rule(
    rule_type: str,
    operator: str,
    *,
    value: object = None,
    min: float | None = None,
    max: float | None = None,
    in_: list[str] | None = None,
    logic_group: int = 0,
    description: str = "test",
    confidence: float = 0.9,
) -> EligibilityRule:
    rv = RuleValue(value=value, min=min, max=max, **{"in": in_})
    return EligibilityRule(
        rule_type=rule_type,  # type: ignore[arg-type]
        operator=operator,  # type: ignore[arg-type]
        value=rv,
        logic_group=logic_group,
        description=description,
        confidence=confidence,
    )


class TestSummarizeRulesBasic:
    def test_empty_rules(self) -> None:
        assert summarize_rules([]) == ""

    def test_custom_rules_skipped(self) -> None:
        r = _rule("custom", "eq", value="some condition")
        assert summarize_rules([r]) == ""

    def test_age_between(self) -> None:
        r = _rule("age", "between", min=18.0, max=60.0)
        assert summarize_rules([r]) == "age 18-60"

    def test_age_gte_only(self) -> None:
        r = _rule("age", "gte", value=21)
        assert summarize_rules([r]) == "age 21+"

    def test_age_lte_only(self) -> None:
        r = _rule("age", "lte", value=35)
        assert summarize_rules([r]) == "age up to 35"

    def test_age_gte_and_lte(self) -> None:
        r1 = _rule("age", "gte", value=18)
        r2 = _rule("age", "lte", value=40)
        summary = summarize_rules([r1, r2])
        assert "age 18-40" in summary

    def test_income_lte(self) -> None:
        r = _rule("income", "lte", value=300_000)
        assert summarize_rules([r]) == "income up to ₹3L"

    def test_income_lte_small(self) -> None:
        r = _rule("income", "lte", value=50_000)
        assert summarize_rules([r]) == "income up to ₹50,000"

    def test_gender_female(self) -> None:
        r = _rule("gender", "eq", value="female")
        assert summarize_rules([r]) == "women"

    def test_gender_male(self) -> None:
        r = _rule("gender", "eq", value="male")
        assert summarize_rules([r]) == "men"

    def test_state_single(self) -> None:
        r = _rule("state", "eq", value="Karnataka")
        assert summarize_rules([r]) == "Karnataka residents"

    def test_state_multiple_in(self) -> None:
        r = _rule("state", "in", in_=["Karnataka", "Kerala", "Tamil Nadu"])
        summary = summarize_rules([r])
        assert "residents" in summary
        assert "Karnataka" in summary

    def test_caste_in(self) -> None:
        r = _rule("caste_category", "in", in_=["SC", "ST", "OBC"])
        assert summarize_rules([r]) == "SC/ST/OBC"

    def test_caste_eq(self) -> None:
        r = _rule("caste_category", "eq", value="SC")
        assert summarize_rules([r]) == "SC"

    def test_is_farmer_true(self) -> None:
        r = _rule("is_farmer", "eq", value=True)
        assert summarize_rules([r]) == "farmers"

    def test_is_farmer_false_skipped(self) -> None:
        r = _rule("is_farmer", "eq", value=False)
        assert summarize_rules([r]) == ""

    def test_land_lte(self) -> None:
        r = _rule("land_holding_acres", "lte", value=5.0)
        assert summarize_rules([r]) == "land up to 5 acres"

    def test_land_fractional(self) -> None:
        r = _rule("land_holding_acres", "lte", value=2.5)
        assert summarize_rules([r]) == "land up to 2.5 acres"

    def test_has_disability_true(self) -> None:
        r = _rule("has_disability", "eq", value=True)
        assert summarize_rules([r]) == "persons with disabilities"

    def test_disability_percentage_gte(self) -> None:
        r = _rule("disability_percentage", "gte", value=40)
        assert summarize_rules([r]) == "40%+ disability"

    def test_education_in(self) -> None:
        r = _rule("education_level", "in", in_=["masters_degree", "phd"])
        summary = summarize_rules([r])
        assert "postgraduates" in summary
        assert "PhD" in summary

    def test_religion_minority(self) -> None:
        r = _rule("religion", "eq", value="minority")
        assert summarize_rules([r]) == "minority communities"

    def test_occupation_in(self) -> None:
        r = _rule("occupation", "in", in_=["farmer", "artisan", "weaver"])
        summary = summarize_rules([r])
        assert "farmer" in summary

    def test_marital_status_widowed(self) -> None:
        r = _rule("marital_status", "eq", value="widowed")
        assert summarize_rules([r]) == "widowed"


class TestSummarizeRulesCombined:
    def test_farmer_scheme_multiple_rules(self) -> None:
        rules = [
            _rule("is_farmer", "eq", value=True),
            _rule("land_holding_acres", "lte", value=5.0),
            _rule("state", "eq", value="Karnataka"),
            _rule("custom", "eq", value="must be registered"),
        ]
        summary = summarize_rules(rules)
        assert "farmers" in summary
        assert "land up to 5 acres" in summary
        assert "Karnataka residents" in summary
        # custom skipped
        assert "registered" not in summary

    def test_sc_st_scholarship(self) -> None:
        rules = [
            _rule("caste_category", "in", in_=["SC", "ST"]),
            _rule("income", "lte", value=250_000),
            _rule("education_level", "in", in_=["graduate", "masters_degree"]),
        ]
        summary = summarize_rules(rules)
        assert "SC/ST" in summary
        assert "income" in summary

    def test_disability_scheme(self) -> None:
        rules = [
            _rule("has_disability", "eq", value=True),
            _rule("disability_percentage", "gte", value=40),
            _rule("age", "between", min=18.0, max=59.0),
        ]
        summary = summarize_rules(rules)
        assert "persons with disabilities" in summary
        assert "40%+ disability" in summary
        assert "age 18-59" in summary

    def test_summary_capped_at_200_chars(self) -> None:
        rules = [
            _rule("state", "in", in_=["A", "B", "C", "D", "E"]),
            _rule("caste_category", "in", in_=["SC", "ST", "OBC", "EWS", "GEN"]),
            _rule("occupation", "in", in_=["farmer", "artisan", "weaver", "potter"]),
            _rule("age", "between", min=18.0, max=60.0),
            _rule("income", "lte", value=300_000),
            _rule("gender", "eq", value="female"),
            _rule("marital_status", "eq", value="widowed"),
            _rule("religion", "eq", value="minority"),
        ]
        summary = summarize_rules(rules)
        assert len(summary) <= 200

    def test_only_custom_rules_returns_empty(self) -> None:
        rules = [
            _rule("custom", "eq", value="condition 1"),
            _rule("custom", "eq", value="condition 2"),
        ]
        assert summarize_rules(rules) == ""

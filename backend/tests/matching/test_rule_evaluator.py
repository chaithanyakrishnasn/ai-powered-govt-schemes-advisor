import pytest

from app.db.models import EligibilityRule
from app.schemas.user_profile import UserProfile
from app.services.matching.rule_evaluator import RuleEvaluator, RuleOutcome


def make_rule(rule_type: str, operator: str, value: dict) -> EligibilityRule:
    return EligibilityRule(
        id=1, scheme_id=1, rule_type=rule_type, operator=operator, value=value,
        logic_group=0, group_operator="AND", is_required=True, description="Test rule", confidence=1.0
    )

@pytest.mark.parametrize("age, op, val, outcome", [
    (30, "eq", 30, RuleOutcome.PASS),
    (30, "neq", 31, RuleOutcome.PASS),
    (30, "lt", 31, RuleOutcome.PASS),
    (30, "lte", 30, RuleOutcome.PASS),
    (30, "gt", 29, RuleOutcome.PASS),
    (30, "gte", 30, RuleOutcome.PASS),
    (30, "between", {"min": 20, "max": 40}, RuleOutcome.PASS),
    (30, "eq", 31, RuleOutcome.FAIL),
])
def test_evaluate_age(age, op, val, outcome):
    rule = make_rule("age", op, val if isinstance(val, dict) else {"value": val})
    profile = UserProfile(age=age)
    result = RuleEvaluator.evaluate(rule, profile)
    assert result.outcome == outcome

def test_evaluate_age_unknown():
    rule = make_rule("age", "eq", {"value": 30})
    profile = UserProfile(age=None)
    result = RuleEvaluator.evaluate(rule, profile)
    assert result.outcome == RuleOutcome.UNKNOWN

@pytest.mark.parametrize("income, op, val, outcome", [
    (50000, "lte", 60000, RuleOutcome.PASS),
    (50000, "lt", 40000, RuleOutcome.FAIL),
])
def test_evaluate_income(income, op, val, outcome):
    rule = make_rule("income", op, {"value": val})
    profile = UserProfile(annual_income=income)
    result = RuleEvaluator.evaluate(rule, profile)
    assert result.outcome == outcome

@pytest.mark.parametrize("religion, rule_val, outcome", [
    ("Muslim", "minority", RuleOutcome.PASS),
    ("Hindu", "minority", RuleOutcome.FAIL),
    ("Jain", "minority", RuleOutcome.PASS),
    ("Sikh", "minority", RuleOutcome.PASS),
])
def test_evaluate_religion_minority(religion, rule_val, outcome):
    rule = make_rule("religion", "eq", {"value": rule_val})
    profile = UserProfile(religion=religion)
    result = RuleEvaluator.evaluate(rule, profile)
    assert result.outcome == outcome

@pytest.mark.parametrize("education, op, rule_val, outcome", [
    ("graduate", "gte", "secondary", RuleOutcome.PASS),
    ("primary", "gte", "secondary", RuleOutcome.FAIL),
    ("graduate", "eq", "graduate", RuleOutcome.PASS),
    ("masters_degree", "eq", "postgraduate", RuleOutcome.PASS),
])
def test_evaluate_education_level(education, op, rule_val, outcome):
    rule = make_rule("education_level", op, {"value": rule_val})
    profile = UserProfile(education_level=education)
    result = RuleEvaluator.evaluate(rule, profile)
    assert result.outcome == outcome

def test_evaluate_has_disability_inference():
    rule = make_rule("has_disability", "eq", {"value": True})
    profile = UserProfile(has_disability=None, disability_percentage=40)
    result = RuleEvaluator.evaluate(rule, profile)
    assert result.outcome == RuleOutcome.PASS

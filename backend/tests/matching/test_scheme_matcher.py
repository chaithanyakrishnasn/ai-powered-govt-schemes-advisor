from app.db.models import EligibilityRule, Scheme
from app.schemas.user_profile import UserProfile
from app.services.matching.scheme_matcher import EligibilityStatus, SchemeMatcher


def make_rule(rule_type: str, operator: str, value: dict, logic_group: int = 0, confidence: float = 1.0) -> EligibilityRule:
    return EligibilityRule(
        id=1, scheme_id=1, rule_type=rule_type, operator=operator, value=value,
        logic_group=logic_group, group_operator="AND", is_required=True, description="Test rule", confidence=confidence
    )

def make_scheme(rules: list[EligibilityRule]) -> Scheme:
    return Scheme(
        id=1, slug="test-scheme", name="Test Scheme", eligibility_rules=rules
    )

def test_all_pass_is_eligible():
    rules = [make_rule("age", "eq", {"value": 30})]
    scheme = make_scheme(rules)
    profile = UserProfile(age=30)
    result = SchemeMatcher.match(scheme, profile)
    assert result.status == EligibilityStatus.ELIGIBLE
    assert result.score == 1.0

def test_one_fail_is_not_eligible():
    rules = [
        make_rule("age", "eq", {"value": 30}),
        make_rule("state", "eq", {"value": "Karnataka"}),
    ]
    scheme = make_scheme(rules)
    profile = UserProfile(age=30, state="Maharashtra")
    result = SchemeMatcher.match(scheme, profile)
    assert result.status == EligibilityStatus.NOT_ELIGIBLE
    assert result.score == 0.0
    assert len(result.failed_rules) == 1

def test_all_unknown_is_need_more_info():
    rules = [make_rule("age", "eq", {"value": 30})]
    scheme = make_scheme(rules)
    profile = UserProfile()
    result = SchemeMatcher.match(scheme, profile)
    assert result.status == EligibilityStatus.NEED_MORE_INFO
    assert result.score > 0.0
    assert "age" in result.missing_fields

def test_pass_and_unknown_is_likely_eligible():
    rules = [
        make_rule("age", "eq", {"value": 30}),
        make_rule("state", "eq", {"value": "Karnataka"}),
    ]
    scheme = make_scheme(rules)
    profile = UserProfile(age=30)
    result = SchemeMatcher.match(scheme, profile)
    assert result.status == EligibilityStatus.LIKELY_ELIGIBLE
    assert 0.7 < result.score < 1.0
    assert "state" in result.missing_fields

def test_all_custom_is_need_more_info():
    rules = [make_rule("custom", "eq", {"value": "some custom rule"})]
    scheme = make_scheme(rules)
    profile = UserProfile()
    result = SchemeMatcher.match(scheme, profile)
    assert result.status == EligibilityStatus.NEED_MORE_INFO
    assert result.score == 0.3

def test_empty_rules_is_need_more_info():
    scheme = make_scheme([])
    profile = UserProfile()
    result = SchemeMatcher.match(scheme, profile)
    assert result.status == EligibilityStatus.NEED_MORE_INFO
    assert result.score == 0.3

def test_score_is_diluted_by_confidence():
    rules = [make_rule("age", "eq", {"value": 30}, confidence=0.5)]
    scheme = make_scheme(rules)
    profile = UserProfile(age=30)
    result = SchemeMatcher.match(scheme, profile)
    assert result.status == EligibilityStatus.ELIGIBLE
    assert result.score == 0.5

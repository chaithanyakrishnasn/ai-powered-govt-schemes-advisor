"""Unit tests for schemas, validators, and extractor (no live network calls)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from pydantic import ValidationError

from app.services.extraction.schemas import (
    EligibilityRule,
    ExtractionResult,
    RuleValue,
    SchemeContext,
)
from app.services.extraction.validators import (
    INDIAN_STATES_UTS,
    KNOWN_CASTE_CODES,
    validate_rules,
)

GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.json"


# ── RuleValue ────────────────────────────────────────────────────────────────

class TestRuleValue:
    def test_scalar_value(self) -> None:
        rv = RuleValue(value=42)
        assert rv.value == 42

    def test_range_value(self) -> None:
        rv = RuleValue(min=18.0, max=60.0)
        assert rv.min == 18.0
        assert rv.max == 60.0

    def test_list_value_via_alias(self) -> None:
        rv = RuleValue.model_validate({"in": ["SC", "ST"]})
        assert rv.in_ == ["SC", "ST"]

    def test_serializes_alias(self) -> None:
        rv = RuleValue.model_validate({"in": ["SC"]})
        dumped = rv.model_dump(by_alias=True)
        assert "in" in dumped
        assert dumped["in"] == ["SC"]


# ── EligibilityRule operator/value compat ───────────────────────────────────

class TestEligibilityRuleValidation:
    def _make(self, operator: str, value: dict[str, Any]) -> EligibilityRule:
        return EligibilityRule(
            rule_type="age",
            operator=operator,  # type: ignore[arg-type]
            value=RuleValue.model_validate(value),
            description="test rule",
            confidence=0.9,
        )

    def test_scalar_operators_require_value(self) -> None:
        for op in ["eq", "neq", "lt", "lte", "gt", "gte"]:
            rule = self._make(op, {"value": 42})
            assert rule.operator == op

    def test_scalar_operator_fails_without_value(self) -> None:
        with pytest.raises((ValueError, ValidationError)):
            self._make("eq", {"min": 10.0, "max": 20.0})

    def test_between_requires_min_and_max(self) -> None:
        rule = self._make("between", {"min": 18.0, "max": 60.0})
        assert rule.value.min == 18.0

    def test_between_fails_missing_max(self) -> None:
        with pytest.raises((ValueError, ValidationError)):
            self._make("between", {"min": 18.0})

    def test_between_fails_min_gte_max(self) -> None:
        with pytest.raises((ValueError, ValidationError)):
            self._make("between", {"min": 60.0, "max": 18.0})

    def test_in_requires_list(self) -> None:
        rule = EligibilityRule(
            rule_type="caste_category",
            operator="in",
            value=RuleValue.model_validate({"in": ["SC", "ST"]}),
            description="caste rule",
            confidence=0.95,
        )
        assert rule.value.in_ == ["SC", "ST"]

    def test_in_fails_without_list(self) -> None:
        with pytest.raises((ValueError, ValidationError)):
            EligibilityRule(
                rule_type="caste_category",
                operator="in",
                value=RuleValue(value="SC"),
                description="bad",
                confidence=0.9,
            )

    def test_description_max_length(self) -> None:
        with pytest.raises((ValueError, ValidationError)):
            EligibilityRule(
                rule_type="age",
                operator="gte",
                value=RuleValue(value=18),
                description="x" * 201,
                confidence=0.9,
            )

    def test_confidence_bounds(self) -> None:
        with pytest.raises((ValueError, ValidationError)):
            EligibilityRule(
                rule_type="age",
                operator="eq",
                value=RuleValue(value=18),
                description="bad conf",
                confidence=1.5,
            )


# ── Validators ───────────────────────────────────────────────────────────────

def _rule(
    rule_type: str,
    operator: str,
    value_dict: dict[str, Any],
    logic_group: int = 0,
    confidence: float = 0.9,
) -> EligibilityRule:
    return EligibilityRule(
        rule_type=rule_type,  # type: ignore[arg-type]
        operator=operator,  # type: ignore[arg-type]
        value=RuleValue.model_validate(value_dict),
        logic_group=logic_group,
        description="test",
        confidence=confidence,
    )


class TestValidateRules:
    def test_valid_age_rule_passes(self) -> None:
        rules = [_rule("age", "between", {"min": 18.0, "max": 60.0})]
        report = validate_rules(rules)
        assert len(report.passing_rules) == 1
        assert len(report.errors) == 0

    def test_age_too_high_is_error(self) -> None:
        rules = [_rule("age", "lte", {"value": 200})]
        report = validate_rules(rules)
        assert len(report.errors) == 1
        assert len(report.passing_rules) == 0

    def test_age_negative_is_error(self) -> None:
        rules = [_rule("age", "gte", {"value": -5})]
        report = validate_rules(rules)
        assert len(report.errors) == 1

    def test_income_over_max_is_error(self) -> None:
        rules = [_rule("income", "lte", {"value": 50_000_000})]
        report = validate_rules(rules)
        assert len(report.errors) == 1

    def test_income_zero_passes(self) -> None:
        rules = [_rule("income", "gte", {"value": 0})]
        report = validate_rules(rules)
        assert len(report.passing_rules) == 1

    def test_land_over_max_is_error(self) -> None:
        rules = [_rule("land_holding_acres", "lte", {"value": 1500.0})]
        report = validate_rules(rules)
        assert len(report.errors) == 1

    def test_disability_over_100_is_error(self) -> None:
        rules = [_rule("disability_percentage", "gte", {"value": 150})]
        report = validate_rules(rules)
        assert len(report.errors) == 1

    def test_known_caste_passes(self) -> None:
        for code in KNOWN_CASTE_CODES:
            rules = [
                EligibilityRule(
                    rule_type="caste_category",
                    operator="in",
                    value=RuleValue.model_validate({"in": [code]}),
                    description="caste",
                    confidence=0.9,
                )
            ]
            report = validate_rules(rules)
            assert len(report.errors) == 0, f"Expected no errors for {code}"

    def test_unknown_caste_is_error(self) -> None:
        rules = [
            EligibilityRule(
                rule_type="caste_category",
                operator="in",
                value=RuleValue.model_validate({"in": ["UNKNOWN_CASTE"]}),
                description="caste",
                confidence=0.9,
            )
        ]
        report = validate_rules(rules)
        assert len(report.errors) == 1

    def test_known_state_passes(self) -> None:
        rules = [_rule("state", "eq", {"value": "Karnataka"})]
        report = validate_rules(rules)
        assert len(report.errors) == 0
        assert len(report.passing_rules) == 1

    def test_unknown_state_is_warning(self) -> None:
        rules = [_rule("state", "eq", {"value": "Atlantis"})]
        report = validate_rules(rules)
        assert len(report.warnings) == 1
        assert len(report.errors) == 0  # warning, not error
        assert len(report.passing_rules) == 1  # still passes

    def test_all_states_uts_recognized(self) -> None:
        for s in INDIAN_STATES_UTS:
            rules = [_rule("state", "eq", {"value": s})]
            report = validate_rules(rules)
            assert len(report.warnings) == 0, f"Unexpected warning for state: {s}"

    def test_duplicate_rule_type_same_group_warns(self) -> None:
        rules = [
            _rule("age", "gte", {"value": 18}, logic_group=0),
            _rule("age", "lte", {"value": 60}, logic_group=0),
        ]
        report = validate_rules(rules)
        assert len(report.warnings) == 1
        assert len(report.passing_rules) == 2  # both pass

    def test_mixed_valid_invalid(self) -> None:
        rules = [
            _rule("age", "between", {"min": 18.0, "max": 60.0}),
            _rule("age", "gte", {"value": 999}),  # error: out of range
            _rule("income", "lte", {"value": 200000}),
        ]
        report = validate_rules(rules)
        assert len(report.passing_rules) == 2
        assert len(report.errors) == 1


# ── ExtractionResult ─────────────────────────────────────────────────────────

class TestExtractionResult:
    def test_empty_rules(self) -> None:
        er = ExtractionResult(
            rules=[],
            has_unstructured_remainder=True,
            unstructured_remainder="some text",
            overall_confidence=0.3,
        )
        assert er.rules == []
        assert er.has_unstructured_remainder is True

    def test_overall_confidence_bounds(self) -> None:
        with pytest.raises((ValueError, ValidationError)):
            ExtractionResult(rules=[], overall_confidence=1.5)


# ── SchemeContext ─────────────────────────────────────────────────────────────

class TestSchemeContext:
    def test_defaults(self) -> None:
        ctx = SchemeContext()
        assert ctx.level == "central"
        assert ctx.state is None


# ── Golden set parses cleanly ────────────────────────────────────────────────

class TestGoldenSetParseable:
    def test_golden_set_loads(self) -> None:
        data = json.loads(GOLDEN_SET_PATH.read_text())
        assert len(data) >= 15

    def test_all_expected_rules_are_valid_pydantic(self) -> None:
        data = json.loads(GOLDEN_SET_PATH.read_text())
        for entry in data:
            expected = entry["expected"]
            result = ExtractionResult(
                rules=[EligibilityRule.model_validate(r) for r in expected["rules"]],
                has_unstructured_remainder=expected.get("has_unstructured_remainder", False),
                overall_confidence=expected.get("overall_confidence", 0.9),
            )
            assert isinstance(result, ExtractionResult), f"Failed for {entry['id']}"


# ── Extractor (mocked) ───────────────────────────────────────────────────────

class TestEligibilityExtractorMocked:
    @pytest.fixture
    def mock_result(self) -> ExtractionResult:
        return ExtractionResult(
            rules=[
                EligibilityRule(
                    rule_type="age",
                    operator="between",
                    value=RuleValue(min=18.0, max=60.0),
                    description="Age between 18 and 60",
                    confidence=0.95,
                ),
            ],
            overall_confidence=0.95,
        )

    @pytest.fixture
    def mock_gemini(self, mock_result: ExtractionResult) -> MagicMock:
        mock = MagicMock()
        mock_instructor = MagicMock()

        # create_with_completion returns (result, completion)
        mock_completion = MagicMock()
        mock_completion.usage_metadata = None
        mock_instructor.chat.completions.create_with_completion = AsyncMock(
            return_value=(mock_result, mock_completion)
        )
        mock.instructor_client = mock_instructor
        return mock

    @pytest.mark.asyncio
    async def test_extract_returns_result(
        self, mock_gemini: MagicMock, mock_result: ExtractionResult
    ) -> None:
        from app.services.extraction.extractor import EligibilityExtractor

        extractor = EligibilityExtractor(mock_gemini, rpm_limit=100)
        ctx = SchemeContext(scheme_name="Test", level="central")
        result = await extractor.extract("Some eligibility text", ctx)
        assert len(result.rules) == 1
        assert result.rules[0].rule_type == "age"

    @pytest.mark.asyncio
    async def test_extract_drops_invalid_rules(self, mock_gemini: MagicMock) -> None:
        from app.services.extraction.extractor import EligibilityExtractor

        bad_result = ExtractionResult(
            rules=[
                EligibilityRule(
                    rule_type="age",
                    operator="gte",
                    value=RuleValue(value=999),  # out of range
                    description="Bad age",
                    confidence=0.9,
                ),
            ],
            overall_confidence=0.5,
        )
        mock_completion = MagicMock()
        mock_completion.usage_metadata = None
        mock_gemini.instructor_client.chat.completions.create_with_completion = AsyncMock(
            return_value=(bad_result, mock_completion)
        )

        extractor = EligibilityExtractor(mock_gemini, rpm_limit=100)
        result = await extractor.extract("some text")
        assert len(result.rules) == 0

    @pytest.mark.asyncio
    async def test_extract_batch_returns_list(
        self, mock_gemini: MagicMock, mock_result: ExtractionResult
    ) -> None:
        from app.services.extraction.extractor import EligibilityExtractor

        extractor = EligibilityExtractor(mock_gemini, rpm_limit=100)
        items = [
            ("text 1", SchemeContext(scheme_name="Scheme A")),
            ("text 2", SchemeContext(scheme_name="Scheme B")),
        ]
        results = await extractor.extract_batch(items, concurrency=2)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_extract_batch_handles_exception(self, mock_gemini: MagicMock) -> None:
        from app.services.extraction.extractor import EligibilityExtractor

        mock_gemini.instructor_client.chat.completions.create_with_completion = AsyncMock(
            side_effect=RuntimeError("API error")
        )
        extractor = EligibilityExtractor(mock_gemini, rpm_limit=100)
        items = [("text", SchemeContext(scheme_name="Failing Scheme"))]
        results = await extractor.extract_batch(items)
        assert len(results) == 1
        assert results[0].rules == []
        assert results[0].overall_confidence == 0.0

    @pytest.mark.asyncio
    async def test_extractor_failure_propagation(self, mock_gemini: MagicMock) -> None:
        """When the Instructor call raises, extract() returns failed=True with the reason."""
        from app.services.extraction.extractor import EligibilityExtractor

        mock_gemini.instructor_client.chat.completions.create_with_completion = AsyncMock(
            side_effect=ValueError("No API key was provided")
        )
        extractor = EligibilityExtractor(mock_gemini, rpm_limit=100)
        result = await extractor.extract("some eligibility text", SchemeContext(scheme_name="Test"))
        assert result.failed is True
        assert result.failure_reason is not None
        assert "No API key" in result.failure_reason
        assert result.rules == []
        assert result.overall_confidence == 0.0

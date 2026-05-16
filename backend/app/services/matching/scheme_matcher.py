from __future__ import annotations

import statistics
from collections import defaultdict
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import Scheme
from app.schemas.user_profile import UserProfile
from app.services.matching.rule_evaluator import (
    RuleEvaluation,
    RuleEvaluator,
    RuleOutcome,
)


class EligibilityStatus(StrEnum):
    ELIGIBLE = "eligible"
    LIKELY_ELIGIBLE = "likely_eligible"
    NEED_MORE_INFO = "need_more_info"
    NOT_ELIGIBLE = "not_eligible"


class SchemeMatchResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    scheme_id: int
    slug: str
    name: str
    status: EligibilityStatus
    score: float = Field(..., ge=0.0, le=1.0)
    rule_evaluations: list[RuleEvaluation]
    missing_fields: list[str] = Field(default_factory=list)
    failed_rules: list[RuleEvaluation] = Field(default_factory=list)
    semantic_similarity: float | None = None
    combined_score: float | None = None


class SchemeMatcher:

    # Map rule types to user profile field names to identify missing data.
    RULE_TYPE_TO_PROFILE_FIELD: dict[str, str] = {
        "age": "age",
        "income": "annual_income",
        "gender": "gender",
        "state": "state",
        "caste_category": "caste_category",
        "occupation": "occupation",
        "is_farmer": "is_farmer",
        "land_holding_acres": "land_holding_acres",
        "education_level": "education_level",
        "family_size": "family_size",
        "has_disability": "has_disability",
        "disability_percentage": "disability_percentage",
        "religion": "religion",
        "marital_status": "marital_status",
        "employment_status": "employment_status",
    }

    @staticmethod
    def match(scheme: Scheme, profile: UserProfile) -> SchemeMatchResult:
        evaluations = [RuleEvaluator.evaluate(rule, profile) for rule in scheme.eligibility_rules]
        
        pass_count = sum(1 for ev in evaluations if ev.outcome == RuleOutcome.PASS)
        fail_count = sum(1 for ev in evaluations if ev.outcome == RuleOutcome.FAIL)
        unknown_count = sum(1 for ev in evaluations if ev.outcome == RuleOutcome.UNKNOWN)

        # Vacuous case: all rules were custom/skipped. We cannot determine eligibility.
        # Stage-3 LLM reasoning over raw_eligibility_text handles this.
        if pass_count == 0 and fail_count == 0 and unknown_count == 0:
            return SchemeMatchResult(
                scheme_id=scheme.id,
                slug=scheme.slug,
                name=scheme.name,
                status=EligibilityStatus.NEED_MORE_INFO,
                score=0.3,
                rule_evaluations=evaluations,
                missing_fields=[],
                failed_rules=[],
            )

        grouped_evals = defaultdict(list)
        for ev in evaluations:
            if ev.outcome != RuleOutcome.SKIP:
                grouped_evals[ev.rule.logic_group].append(ev)

        group_outcomes: dict[int, RuleOutcome] = {}
        for group_id, group_evals in grouped_evals.items():
            if any(ev.outcome == RuleOutcome.FAIL for ev in group_evals):
                group_outcomes[group_id] = RuleOutcome.FAIL
            elif any(ev.outcome == RuleOutcome.UNKNOWN for ev in group_evals):
                group_outcomes[group_id] = RuleOutcome.UNKNOWN
            else:
                group_outcomes[group_id] = RuleOutcome.PASS
        
        final_outcome: RuleOutcome
        if not group_outcomes:
            final_outcome = RuleOutcome.PASS
        elif any(outcome == RuleOutcome.FAIL for outcome in group_outcomes.values()):
            final_outcome = RuleOutcome.FAIL
        elif any(outcome == RuleOutcome.UNKNOWN for outcome in group_outcomes.values()):
            final_outcome = RuleOutcome.UNKNOWN
        else:
            final_outcome = RuleOutcome.PASS
        
        status: EligibilityStatus
        if final_outcome == RuleOutcome.FAIL:
            status = EligibilityStatus.NOT_ELIGIBLE
        elif final_outcome == RuleOutcome.PASS:
            status = EligibilityStatus.ELIGIBLE
        elif final_outcome == RuleOutcome.UNKNOWN:
            if pass_count > 0:
                status = EligibilityStatus.LIKELY_ELIGIBLE
            else:
                status = EligibilityStatus.NEED_MORE_INFO
        else:
            status = EligibilityStatus.NEED_MORE_INFO

        missing_fields = sorted(list(set(
            SchemeMatcher.RULE_TYPE_TO_PROFILE_FIELD[ev.rule.rule_type]
            for ev in evaluations
            if ev.outcome == RuleOutcome.UNKNOWN and ev.rule.rule_type in SchemeMatcher.RULE_TYPE_TO_PROFILE_FIELD
        )))

        failed_rules = [ev for ev in evaluations if ev.outcome == RuleOutcome.FAIL]
        
        score = SchemeMatcher._calculate_score(status, pass_count, unknown_count, evaluations)

        return SchemeMatchResult(
            scheme_id=scheme.id,
            slug=scheme.slug,
            name=scheme.name,
            status=status,
            score=score,
            rule_evaluations=evaluations,
            missing_fields=missing_fields,
            failed_rules=failed_rules,
        )

    @staticmethod
    def _calculate_score(
        status: EligibilityStatus,
        pass_count: int,
        unknown_count: int,
        evaluations: list[RuleEvaluation],
    ) -> float:
        base_score: float
        if status == EligibilityStatus.ELIGIBLE:
            base_score = 1.0
        elif status == EligibilityStatus.LIKELY_ELIGIBLE:
            base_score = 0.7 + 0.3 * (pass_count / (pass_count + unknown_count)) if (pass_count + unknown_count) > 0 else 0.7
        elif status == EligibilityStatus.NEED_MORE_INFO:
            base_score = 0.3
        else:
            base_score = 0.0

        confidences = [
            float(ev.rule.confidence)
            for ev in evaluations
            if ev.outcome != RuleOutcome.SKIP and ev.rule.confidence is not None
        ]
        avg_confidence = statistics.mean(confidences) if confidences else 1.0
        
        return round(base_score * avg_confidence, 4)

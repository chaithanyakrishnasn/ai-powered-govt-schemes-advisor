from __future__ import annotations

import operator
from collections.abc import Callable
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.db.models import EligibilityRule
from app.schemas.user_profile import UserProfile

# State normalization mapping for all 28 states and 8 UTs
# fmt: off
STATE_NORMALIZATION_MAP = {
    "andhra pradesh": "Andhra Pradesh", "arunachal pradesh": "Arunachal Pradesh", "assam": "Assam",
    "bihar": "Bihar", "chhattisgarh": "Chhattisgarh", "goa": "Goa", "gujarat": "Gujarat",
    "haryana": "Haryana", "himachal pradesh": "Himachal Pradesh", "jharkhand": "Jharkhand",
    "karnataka": "Karnataka", "ka": "Karnataka", "kerala": "Kerala", "madhya pradesh": "Madhya Pradesh",
    "maharashtra": "Maharashtra", "manipur": "Manipur", "meghalaya": "Meghalaya", "mizoram": "Mizoram",
    "nagaland": "Nagaland", "odisha": "Odisha", "punjab": "Punjab", "rajasthan": "Rajasthan",
    "sikkim": "Sikkim", "tamil nadu": "Tamil Nadu", "telangana": "Telangana", "tripura": "Tripura",
    "uttar pradesh": "Uttar Pradesh", "uttarakhand": "Uttarakhand", "west bengal": "West Bengal",
    "andaman and nicobar islands": "Andaman and Nicobar Islands", "an": "Andaman and Nicobar Islands",
    "chandigarh": "Chandigarh", "dadra and nagar haveli and daman and diu": "Dadra and Nagar Haveli and Daman and Diu",
    "delhi": "Delhi", "dl": "Delhi", "jammu and kashmir": "Jammu and Kashmir", "jk": "Jammu and Kashmir",
    "ladakh": "Ladakh", "lakshadweep": "Lakshadweep", "puducherry": "Puducherry",
}
# fmt: on

# Ordinal mapping for education levels
EDUCATION_LEVEL_ORDINAL = {
    "none": 0, "primary": 1, "secondary": 2, "higher_secondary": 3, "diploma": 4,
    "graduate": 5, "postgraduate": 6, "masters_degree": 6, "phd": 7,
}

# Notified minority communities in India per NCMEI Act, 2004
MINORITY_RELIGIONS = {"muslim", "christian", "sikh", "buddhist", "jain", "parsi"}


class RuleOutcome(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    UNKNOWN = "unknown"
    SKIP = "skip"


class RuleEvaluation(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    rule: EligibilityRule
    outcome: RuleOutcome
    reason: str


class RuleEvaluator:
    @staticmethod
    def evaluate(rule: EligibilityRule, profile: UserProfile) -> RuleEvaluation:
        eval_method_name = f"_evaluate_{rule.rule_type}"
        eval_method = getattr(RuleEvaluator, eval_method_name, RuleEvaluator._evaluate_default)
        return eval_method(rule, profile)

    @staticmethod
    def _evaluate_default(rule: EligibilityRule, _: UserProfile) -> RuleEvaluation:
        # Default for unhandled rule types is to skip them.
        return RuleEvaluation(
            rule=rule,
            outcome=RuleOutcome.SKIP,
            reason=f"Rule type '{rule.rule_type}' not implemented.",
        )
    
    @staticmethod
    def _evaluate_custom(rule: EligibilityRule, _: UserProfile) -> RuleEvaluation:
        return RuleEvaluation(
            rule=rule,
            outcome=RuleOutcome.SKIP,
            reason="custom rule — evaluated in Stage 3 via LLM reasoning over raw eligibility text",
        )

    @staticmethod
    def _evaluate_age(rule: EligibilityRule, profile: UserProfile) -> RuleEvaluation:
        if profile.age is None:
            return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason="Profile age is not provided.")
        return RuleEvaluator._compare(rule, profile.age)

    @staticmethod
    def _evaluate_income(rule: EligibilityRule, profile: UserProfile) -> RuleEvaluation:
        if profile.annual_income is None:
            return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason="Profile annual_income is not provided.")
        return RuleEvaluator._compare(rule, profile.annual_income)
    
    @staticmethod
    def _evaluate_gender(rule: EligibilityRule, profile: UserProfile) -> RuleEvaluation:
        if profile.gender is None:
            return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason="Profile gender is not provided.")
        return RuleEvaluator._compare(rule, profile.gender)

    @staticmethod
    def _evaluate_state(rule: EligibilityRule, profile: UserProfile) -> RuleEvaluation:
        if profile.state is None:
            return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason="Profile state is not provided.")
        
        normalized_profile_state = STATE_NORMALIZATION_MAP.get(profile.state.lower())
        if not normalized_profile_state:
            return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason=f"Profile state '{profile.state}' could not be normalized.")

        return RuleEvaluator._compare(rule, normalized_profile_state, transform=lambda x: STATE_NORMALIZATION_MAP.get(x.lower(), x))

    @staticmethod
    def _evaluate_caste_category(rule: EligibilityRule, profile: UserProfile) -> RuleEvaluation:
        if profile.caste_category is None:
            return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason="Profile caste_category is not provided.")
        return RuleEvaluator._compare(rule, profile.caste_category)

    @staticmethod
    def _evaluate_occupation(rule: EligibilityRule, profile: UserProfile) -> RuleEvaluation:
        if profile.occupation is None:
            return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason="Profile occupation is not provided.")
        
        eval_result = RuleEvaluator._compare(rule, profile.occupation.lower().strip(), transform=lambda x: x.lower().strip())
        if eval_result.outcome == RuleOutcome.FAIL:
            return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason="Occupation did not match, but treating as UNKNOWN due to fuzzy nature.")
        return eval_result

    @staticmethod
    def _evaluate_is_farmer(rule: EligibilityRule, profile: UserProfile) -> RuleEvaluation:
        if profile.is_farmer is None:
            return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason="Profile is_farmer is not provided.")
        return RuleEvaluator._compare(rule, profile.is_farmer)

    @staticmethod
    def _evaluate_land_holding_acres(rule: EligibilityRule, profile: UserProfile) -> RuleEvaluation:
        if profile.land_holding_acres is None:
            return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason="Profile land_holding_acres is not provided.")
        return RuleEvaluator._compare(rule, profile.land_holding_acres)

    @staticmethod
    def _evaluate_education_level(rule: EligibilityRule, profile: UserProfile) -> RuleEvaluation:
        if profile.education_level is None:
            return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason="Profile education_level is not provided.")
        
        profile_ordinal = EDUCATION_LEVEL_ORDINAL.get(profile.education_level)
        if profile_ordinal is None:
            return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason=f"Unknown education level '{profile.education_level}' in profile.")

        return RuleEvaluator._compare(rule, profile_ordinal, transform=lambda x: EDUCATION_LEVEL_ORDINAL.get(x, -1))

    @staticmethod
    def _evaluate_family_size(rule: EligibilityRule, profile: UserProfile) -> RuleEvaluation:
        if profile.family_size is None:
            return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason="Profile family_size is not provided.")
        return RuleEvaluator._compare(rule, profile.family_size)

    @staticmethod
    def _evaluate_has_disability(rule: EligibilityRule, profile: UserProfile) -> RuleEvaluation:
        profile_val = profile.has_disability
        if profile_val is None:
            if profile.disability_percentage is not None and profile.disability_percentage > 0:
                profile_val = True
            else:
                return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason="Profile has_disability is not provided and cannot be inferred.")
        return RuleEvaluator._compare(rule, profile_val)

    @staticmethod
    def _evaluate_disability_percentage(rule: EligibilityRule, profile: UserProfile) -> RuleEvaluation:
        if profile.disability_percentage is None:
            return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason="Profile disability_percentage is not provided.")
        return RuleEvaluator._compare(rule, profile.disability_percentage)

    @staticmethod
    def _evaluate_religion(rule: EligibilityRule, profile: UserProfile) -> RuleEvaluation:
        if profile.religion is None:
            return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason="Profile religion is not provided.")
        
        rule_value = rule.value.get("value")
        if isinstance(rule_value, str) and rule_value.lower() == "minority":
             profile_religion_lower = profile.religion.lower()
             if profile_religion_lower in MINORITY_RELIGIONS:
                 return RuleEvaluation(rule=rule, outcome=RuleOutcome.PASS, reason=f"Profile religion '{profile.religion}' is a notified minority.")
             else:
                 return RuleEvaluation(rule=rule, outcome=RuleOutcome.FAIL, reason=f"Profile religion '{profile.religion}' is not a notified minority.")

        return RuleEvaluator._compare(rule, profile.religion, transform=lambda x: x.lower())
    
    @staticmethod
    def _evaluate_marital_status(rule: EligibilityRule, profile: UserProfile) -> RuleEvaluation:
        if profile.marital_status is None:
            return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason="Profile marital_status is not provided.")
        return RuleEvaluator._compare(rule, profile.marital_status)

    @staticmethod
    def _evaluate_employment_status(rule: EligibilityRule, profile: UserProfile) -> RuleEvaluation:
        if profile.employment_status is None:
            return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason="Profile employment_status is not provided.")
        return RuleEvaluator._compare(rule, profile.employment_status)

    @staticmethod
    def _compare(rule: EligibilityRule, profile_value: Any, transform: Callable[[Any], Any] | None = None) -> RuleEvaluation:
        op_map = {
            "eq": operator.eq, "neq": operator.ne, "lt": operator.lt,
            "lte": operator.le, "gt": operator.gt, "gte": operator.ge,
        }

        rule_val = rule.value.get("value")
        if transform and rule_val is not None:
            rule_val = transform(rule_val)
            
        op = rule.operator
        reason = f"Profile value '{profile_value}' {op} Rule value '{rule_val}'"

        if op in op_map:
            if rule_val is None:
                return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason="Rule value is null.")
            try:
                result = op_map[op](profile_value, rule_val)
                return RuleEvaluation(rule=rule, outcome=RuleOutcome.PASS if result else RuleOutcome.FAIL, reason=reason)
            except (TypeError, ValueError):
                return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason=f"Type mismatch for operator '{op}'")

        if op == "between":
            min_val, max_val = rule.value.get("min"), rule.value.get("max")
            if min_val is None or max_val is None:
                 return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason="Rule min/max value is null.")
            reason = f"Profile value '{profile_value}' between '{min_val}' and '{max_val}'"
            try:
                result = min_val <= profile_value <= max_val
                return RuleEvaluation(rule=rule, outcome=RuleOutcome.PASS if result else RuleOutcome.FAIL, reason=reason)
            except (TypeError, ValueError):
                return RuleEvaluation(rule=rule, outcome=RuleOutcome.UNKNOWN, reason="Type mismatch for operator 'between'")
        
        if op in ("in", "not_in"):
            rule_list = rule.value.get("in", [])
            if transform:
                rule_list = [transform(x) for x in rule_list]
            
            reason = f"Profile value '{profile_value}' {'not in' if op == 'not_in' else 'in'} {rule_list}"
            result = (profile_value in rule_list) if op == "in" else (profile_value not in rule_list)
            return RuleEvaluation(rule=rule, outcome=RuleOutcome.PASS if result else RuleOutcome.FAIL, reason=reason)

        return RuleEvaluation(rule=rule, outcome=RuleOutcome.SKIP, reason=f"Operator '{op}' not supported.")

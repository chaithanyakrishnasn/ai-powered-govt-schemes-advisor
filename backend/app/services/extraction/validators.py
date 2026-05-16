from __future__ import annotations

from dataclasses import dataclass, field

from app.services.extraction.schemas import EligibilityRule

KNOWN_CASTE_CODES: frozenset[str] = frozenset({"GEN", "OBC", "SC", "ST", "EWS"})

INDIAN_STATES_UTS: frozenset[str] = frozenset(
    {
        # 28 States
        "Andhra Pradesh",
        "Arunachal Pradesh",
        "Assam",
        "Bihar",
        "Chhattisgarh",
        "Goa",
        "Gujarat",
        "Haryana",
        "Himachal Pradesh",
        "Jharkhand",
        "Karnataka",
        "Kerala",
        "Madhya Pradesh",
        "Maharashtra",
        "Manipur",
        "Meghalaya",
        "Mizoram",
        "Nagaland",
        "Odisha",
        "Punjab",
        "Rajasthan",
        "Sikkim",
        "Tamil Nadu",
        "Telangana",
        "Tripura",
        "Uttar Pradesh",
        "Uttarakhand",
        "West Bengal",
        # 8 Union Territories
        "Andaman and Nicobar Islands",
        "Chandigarh",
        "Dadra and Nagar Haveli and Daman and Diu",
        "Delhi",
        "Jammu and Kashmir",
        "Ladakh",
        "Lakshadweep",
        "Puducherry",
    }
)

_AGE_MIN = 0
_AGE_MAX = 120
_INCOME_MIN = 0
_INCOME_MAX = 10_000_000
_LAND_MIN = 0.0
_LAND_MAX = 1000.0
_DISABILITY_MIN = 0
_DISABILITY_MAX = 100


@dataclass
class RuleIssue:
    rule_index: int
    rule_type: str
    message: str
    is_error: bool  # True → rule dropped; False → warning only


@dataclass
class ValidationReport:
    passing_rules: list[EligibilityRule] = field(default_factory=list)
    warnings: list[RuleIssue] = field(default_factory=list)
    errors: list[RuleIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


def validate_rules(rules: list[EligibilityRule]) -> ValidationReport:
    report = ValidationReport()

    for i, rule in enumerate(rules):
        issues = _check_rule(i, rule)
        errors = [iss for iss in issues if iss.is_error]
        warnings = [iss for iss in issues if not iss.is_error]
        report.warnings.extend(warnings)
        if errors:
            report.errors.extend(errors)
        else:
            report.passing_rules.append(rule)

    _check_cross_rule(report.passing_rules, report)
    return report


# ── Per-rule checks ──────────────────────────────────────────────────────────

def _check_rule(idx: int, rule: EligibilityRule) -> list[RuleIssue]:
    issues: list[RuleIssue] = []
    v = rule.value
    rt = rule.rule_type

    if rt == "age":
        issues.extend(_check_numeric_range(idx, rt, v, _AGE_MIN, _AGE_MAX))

    elif rt == "income":
        issues.extend(_check_numeric_range(idx, rt, v, _INCOME_MIN, _INCOME_MAX))

    elif rt == "land_holding_acres":
        issues.extend(_check_numeric_range(idx, rt, v, _LAND_MIN, _LAND_MAX))

    elif rt == "disability_percentage":
        issues.extend(_check_numeric_range(idx, rt, v, _DISABILITY_MIN, _DISABILITY_MAX))

    elif rt == "caste_category":
        if v.in_ is not None:
            unknown = [c for c in v.in_ if c not in KNOWN_CASTE_CODES]
            if unknown:
                issues.append(
                    RuleIssue(
                        idx,
                        rt,
                        f"Unknown caste codes: {unknown}. Use GEN/OBC/SC/ST/EWS.",
                        is_error=True,
                    )
                )
        elif v.value is not None and str(v.value) not in KNOWN_CASTE_CODES:
            issues.append(
                RuleIssue(
                    idx,
                    rt,
                    f"Unknown caste code: {v.value!r}. Use GEN/OBC/SC/ST/EWS.",
                    is_error=True,
                )
            )

    elif rt == "state":
        state_val = v.value
        if state_val is not None and str(state_val) not in INDIAN_STATES_UTS:
            issues.append(
                RuleIssue(
                    idx,
                    rt,
                    f"Unrecognized state/UT: {state_val!r}. Check spelling and title case.",
                    is_error=False,  # warning only — could be a new UT or typo
                )
            )

    # between: min < max (already enforced by schema, but double-check)
    if (
        rule.operator == "between"
        and v.min is not None
        and v.max is not None
        and v.min >= v.max
    ):
        issues.append(
            RuleIssue(idx, rt, f"'between' has min={v.min} >= max={v.max}", is_error=True)
        )

    # in/not_in: non-empty list (schema enforces, belt-and-suspenders)
    if rule.operator in ("in", "not_in") and (v.in_ is None or len(v.in_) == 0):
        issues.append(
            RuleIssue(idx, rt, "Operator 'in'/'not_in' with empty or missing list", is_error=True)
        )

    return issues


def _check_numeric_range(
    idx: int, rt: str, v: object, lo: float, hi: float
) -> list[RuleIssue]:
    from app.services.extraction.schemas import RuleValue

    assert isinstance(v, RuleValue)
    issues: list[RuleIssue] = []
    for label, num in [("value", v.value), ("min", v.min), ("max", v.max)]:
        if num is not None:
            try:
                n = float(num)
            except (TypeError, ValueError):
                issues.append(RuleIssue(idx, rt, f"Non-numeric {label}={num!r}", is_error=True))
                continue
            if not (lo <= n <= hi):
                issues.append(
                    RuleIssue(
                        idx,
                        rt,
                        f"{label}={n} out of plausible range [{lo}, {hi}] for {rt}",
                        is_error=True,
                    )
                )
    return issues


# ── Cross-rule checks ────────────────────────────────────────────────────────

def _check_cross_rule(rules: list[EligibilityRule], report: ValidationReport) -> None:
    from collections import defaultdict

    # Detect duplicate rule_types within the same logic_group with conflicting operators
    by_group: dict[int, list[EligibilityRule]] = defaultdict(list)
    for r in rules:
        by_group[r.logic_group].append(r)

    for group_id, group_rules in by_group.items():
        from collections import Counter

        type_counts = Counter(r.rule_type for r in group_rules)
        for rt, count in type_counts.items():
            if count > 1:
                # Multiple rules of same type in same group — warn, not error
                report.warnings.append(
                    RuleIssue(
                        -1,
                        rt,
                        f"rule_type='{rt}' appears {count} times in logic_group={group_id}. "
                        "Verify this is intentional (e.g., two separate age bounds).",
                        is_error=False,
                    )
                )

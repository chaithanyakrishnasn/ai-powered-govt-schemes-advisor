from __future__ import annotations

from app.services.extraction.schemas import EligibilityRule

_MAX_SUMMARY_CHARS = 200

_EDU_LABELS: dict[str, str] = {
    "no_education": "no education",
    "illiterate": "illiterate",
    "primary": "primary",
    "upper_primary": "upper primary",
    "secondary": "secondary",
    "higher_secondary": "higher secondary",
    "diploma": "diploma",
    "graduate": "graduates",
    "bachelors_degree": "graduates",
    "masters_degree": "postgraduates",
    "postgraduate": "postgraduates",
    "phd": "PhD",
    "professional_degree": "professional degree",
    "technical": "technical",
}


def summarize_rules(rules: list[EligibilityRule]) -> str:
    """Deterministic one-line English summary from structured rules.

    Used to enrich search_text for semantic retrieval. Skips custom rules.
    """
    if not rules:
        return ""

    by_type: dict[str, list[EligibilityRule]] = {}
    for r in rules:
        if r.rule_type == "custom":
            continue
        by_type.setdefault(r.rule_type, []).append(r)

    parts: list[str] = []
    for rule_type, type_rules in by_type.items():
        fmted = _format_type(rule_type, type_rules)
        if fmted:
            parts.append(fmted)

    result = ", ".join(parts)
    return result[:_MAX_SUMMARY_CHARS]


def _format_type(rule_type: str, rules: list[EligibilityRule]) -> str:
    match rule_type:
        case "age":
            return _fmt_age(rules)
        case "income":
            return _fmt_income(rules)
        case "gender":
            return _fmt_gender(rules)
        case "state":
            return _fmt_state(rules)
        case "caste_category":
            return _fmt_caste(rules)
        case "occupation":
            return _fmt_occupation(rules)
        case "is_farmer":
            return _fmt_is_farmer(rules)
        case "land_holding_acres":
            return _fmt_land(rules)
        case "education_level":
            return _fmt_education(rules)
        case "family_size":
            return _fmt_family_size(rules)
        case "has_disability":
            return _fmt_has_disability(rules)
        case "religion":
            return _fmt_religion(rules)
        case "marital_status":
            return _fmt_marital_status(rules)
        case "employment_status":
            return _fmt_employment(rules)
        case "disability_percentage":
            return _fmt_disability_pct(rules)
        case _:
            return ""


def _money(amount: float) -> str:
    if amount >= 100_000:
        lakh = amount / 100_000
        return f"₹{lakh:.0f}L" if lakh == int(lakh) else f"₹{lakh:.1f}L"
    return f"₹{amount:,.0f}"


def _acres(val: float) -> str:
    return str(int(val)) if val == int(val) else f"{val:.1f}"


def _truthy(val: object) -> bool:
    return val is True or str(val).lower() in ("true", "1", "yes")


def _fmt_age(rules: list[EligibilityRule]) -> str:
    for r in rules:
        if r.operator == "between" and r.value.min is not None and r.value.max is not None:
            return f"age {int(r.value.min)}-{int(r.value.max)}"
    lo = hi = None
    for r in rules:
        if r.operator in ("gte", "gt") and r.value.value is not None:
            lo = int(float(r.value.value))
        elif r.operator in ("lte", "lt") and r.value.value is not None:
            hi = int(float(r.value.value))
    if lo is not None and hi is not None:
        return f"age {lo}-{hi}"
    if lo is not None:
        return f"age {lo}+"
    if hi is not None:
        return f"age up to {hi}"
    for r in rules:
        if r.operator == "eq" and r.value.value is not None:
            return f"age {r.value.value}"
    return ""


def _fmt_income(rules: list[EligibilityRule]) -> str:
    for r in rules:
        if r.operator in ("lte", "lt") and r.value.value is not None:
            return f"income up to {_money(float(r.value.value))}"
        if r.operator in ("gte", "gt") and r.value.value is not None:
            return f"income above {_money(float(r.value.value))}"
        if r.operator == "between" and r.value.min is not None and r.value.max is not None:
            return f"income {_money(r.value.min)}-{_money(r.value.max)}"
    return ""


def _fmt_gender(rules: list[EligibilityRule]) -> str:
    vals: list[str] = []
    for r in rules:
        if r.operator == "eq" and r.value.value is not None:
            g = str(r.value.value).lower()
            vals.append("women" if g == "female" else "men" if g == "male" else g)
        elif r.operator == "in" and r.value.in_:
            for g in r.value.in_:
                gl = g.lower()
                vals.append("women" if gl == "female" else "men" if gl == "male" else gl)
    unique = list(dict.fromkeys(vals))
    return "/".join(unique) if unique else ""


def _fmt_state(rules: list[EligibilityRule]) -> str:
    states: list[str] = []
    for r in rules:
        if r.operator == "eq" and r.value.value is not None:
            states.append(str(r.value.value))
        elif r.operator == "in" and r.value.in_:
            states.extend(r.value.in_)
    unique = list(dict.fromkeys(states))
    if not unique:
        return ""
    if len(unique) == 1:
        return f"{unique[0]} residents"
    return f"{'/'.join(unique[:3])} residents"


def _fmt_caste(rules: list[EligibilityRule]) -> str:
    castes: list[str] = []
    for r in rules:
        if r.operator == "eq" and r.value.value is not None:
            castes.append(str(r.value.value).upper())
        elif r.operator == "in" and r.value.in_:
            castes.extend(c.upper() for c in r.value.in_)
    unique = list(dict.fromkeys(castes))
    return "/".join(unique[:5]) if unique else ""


def _fmt_occupation(rules: list[EligibilityRule]) -> str:
    occ: list[str] = []
    for r in rules:
        if r.operator == "eq" and r.value.value is not None:
            occ.append(str(r.value.value))
        elif r.operator == "in" and r.value.in_:
            occ.extend(r.value.in_)
    unique = list(dict.fromkeys(occ))
    return ", ".join(unique[:4]) if unique else ""


def _fmt_is_farmer(rules: list[EligibilityRule]) -> str:
    for r in rules:
        if r.operator == "eq" and _truthy(r.value.value):
            return "farmers"
    return ""


def _fmt_land(rules: list[EligibilityRule]) -> str:
    for r in rules:
        if r.operator in ("lte", "lt") and r.value.value is not None:
            return f"land up to {_acres(float(r.value.value))} acres"
        if r.operator in ("gte", "gt") and r.value.value is not None:
            return f"land {_acres(float(r.value.value))}+ acres"
        if r.operator == "between" and r.value.min is not None and r.value.max is not None:
            return f"land {_acres(r.value.min)}-{_acres(r.value.max)} acres"
    return ""


def _fmt_education(rules: list[EligibilityRule]) -> str:
    levels: list[str] = []
    for r in rules:
        if r.operator == "eq" and r.value.value is not None:
            levels.append(_EDU_LABELS.get(str(r.value.value).lower(), str(r.value.value)))
        elif r.operator == "in" and r.value.in_:
            levels.extend(_EDU_LABELS.get(v.lower(), v) for v in r.value.in_)
    unique = list(dict.fromkeys(levels))
    return "/".join(unique[:4]) if unique else ""


def _fmt_family_size(rules: list[EligibilityRule]) -> str:
    for r in rules:
        if r.operator in ("lte", "lt") and r.value.value is not None:
            return f"family up to {r.value.value}"
        if r.operator in ("gte", "gt") and r.value.value is not None:
            return f"family {r.value.value}+"
    return ""


def _fmt_has_disability(rules: list[EligibilityRule]) -> str:
    for r in rules:
        if r.operator == "eq" and _truthy(r.value.value):
            return "persons with disabilities"
    return ""


def _fmt_religion(rules: list[EligibilityRule]) -> str:
    vals: list[str] = []
    for r in rules:
        if r.operator == "eq" and r.value.value is not None:
            v = str(r.value.value).lower()
            vals.append("minority communities" if v in ("minority", "minorities") else v)
        elif r.operator == "in" and r.value.in_:
            for rv in r.value.in_:
                v = rv.lower()
                vals.append("minority communities" if v in ("minority", "minorities") else v)
    unique = list(dict.fromkeys(vals))
    return "/".join(unique[:3]) if unique else ""


def _fmt_marital_status(rules: list[EligibilityRule]) -> str:
    vals: list[str] = []
    for r in rules:
        if r.operator == "eq" and r.value.value is not None:
            vals.append(str(r.value.value).lower())
        elif r.operator == "in" and r.value.in_:
            vals.extend(v.lower() for v in r.value.in_)
    unique = list(dict.fromkeys(vals))
    return "/".join(unique) if unique else ""


def _fmt_employment(rules: list[EligibilityRule]) -> str:
    vals: list[str] = []
    for r in rules:
        if r.operator == "eq" and r.value.value is not None:
            vals.append(str(r.value.value).lower())
        elif r.operator == "in" and r.value.in_:
            vals.extend(v.lower() for v in r.value.in_)
    unique = list(dict.fromkeys(vals))
    return "/".join(unique[:3]) if unique else ""


def _fmt_disability_pct(rules: list[EligibilityRule]) -> str:
    for r in rules:
        if r.operator in ("gte", "gt") and r.value.value is not None:
            return f"{int(float(r.value.value))}%+ disability"
        if r.operator in ("lte", "lt") and r.value.value is not None:
            return f"up to {int(float(r.value.value))}% disability"
        if r.operator == "between" and r.value.min is not None and r.value.max is not None:
            return f"{int(r.value.min)}-{int(r.value.max)}% disability"
    return ""

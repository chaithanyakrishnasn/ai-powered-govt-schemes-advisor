"""Transform myScheme.gov.in API responses into RawScheme objects."""

from scrapers.schema import ApplicationMode, BenefitType, RawScheme

_BENEFIT_MAP: dict[str, BenefitType] = {
    "cash": "cash",
    "subsidy": "subsidy",
    "insurance": "insurance",
    "loan": "loan",
    "training": "training",
    "pension": "pension",
    "scholarship": "scholarship",
}


def _normalize_benefit_type(raw: dict | None) -> BenefitType | None:  # type: ignore[type-arg]
    if not raw:
        return None
    val = (raw.get("value") or "").lower().strip()
    return _BENEFIT_MAP.get(val, "other")


def _normalize_application_mode(mode_str: str | None) -> ApplicationMode | None:
    if not mode_str:
        return None
    lower = mode_str.lower()
    has_online = "online" in lower
    has_offline = "offline" in lower
    if has_online and has_offline:
        return "both"
    if has_online:
        return "online"
    if has_offline:
        return "offline"
    return None


def _str_or_none(val: object) -> str | None:
    if not val:
        return None
    s = str(val).strip()
    return s or None


def _label(obj: dict | None) -> str | None:  # type: ignore[type-arg]
    if isinstance(obj, dict):
        return _str_or_none(obj.get("label"))
    return None


def normalize(detail: dict, listing_fields: dict | None = None) -> RawScheme:  # type: ignore[type-arg]
    """
    Build a RawScheme from the detail endpoint response (`data` dict) and
    optionally the listing-endpoint `fields` dict for supplementary data.
    """
    en = detail.get("en", {})
    bd = en.get("basicDetails", {})
    sc = en.get("schemeContent", {})
    ec = en.get("eligibilityCriteria", {}) if isinstance(en.get("eligibilityCriteria"), dict) else {}
    ap_list = en.get("applicationProcess", [])
    ap = ap_list[0] if isinstance(ap_list, list) and ap_list else {}

    slug: str = detail.get("slug", "")

    # level
    level_val = _label(bd.get("level")) or ""
    level = "central" if level_val.lower() == "central" else "state"

    # state — prefer detail basicDetails.state, fall back to listing beneficiaryState
    state: str | None = _label(bd.get("state"))
    if state is None and listing_fields:
        beneficiary_states: list[str] = listing_fields.get("beneficiaryState") or []
        non_all = [s for s in beneficiary_states if s.lower() != "all"]
        if non_all:
            state = non_all[0]

    # ministry — prefer nodalMinistryName, fall back to nodalDepartmentName
    ministry: str | None = _label(bd.get("nodalMinistryName")) or _label(
        bd.get("nodalDepartmentName")
    )

    # categories
    raw_cats = bd.get("schemeCategory") or []
    if isinstance(raw_cats, list):
        categories = [c["label"] for c in raw_cats if isinstance(c, dict) and c.get("label")]
    else:
        categories = []

    # tags
    raw_tags = bd.get("tags") or (listing_fields or {}).get("tags") or []
    tags = [t for t in raw_tags if isinstance(t, str)]

    # description — prefer detailedDescription_md, fall back to briefDescription
    description = _str_or_none(sc.get("detailedDescription_md")) or _str_or_none(
        sc.get("briefDescription")
    )

    # benefit
    raw_bt = sc.get("benefitTypes")
    # benefitTypes can be a dict or list; handle both
    if isinstance(raw_bt, list):
        raw_bt = raw_bt[0] if raw_bt else None
    benefit_type = _normalize_benefit_type(raw_bt)
    benefit_description = _str_or_none(sc.get("benefits_md"))

    # eligibility
    raw_eligibility_text = _str_or_none(ec.get("eligibilityDescription_md"))

    # application
    application_url = _str_or_none(ap.get("url"))
    application_mode = _normalize_application_mode(ap.get("mode"))

    # documents
    raw_docs = en.get("documentsRequired") or sc.get("documentsRequired") or []
    if isinstance(raw_docs, list):
        documents_required = [
            d.get("documentName") or d.get("name") or str(d)
            for d in raw_docs
            if d
        ]
    else:
        documents_required = []

    return RawScheme(
        slug=slug,
        name=bd.get("schemeName") or slug,
        description=description,
        ministry=ministry,
        level=level,
        state=state,
        categories=categories,
        tags=tags,
        benefit_type=benefit_type,
        benefit_description=benefit_description,
        raw_eligibility_text=raw_eligibility_text,
        application_url=application_url,
        application_mode=application_mode,
        documents_required=documents_required,
        source_url=f"https://www.myscheme.gov.in/schemes/{slug}",
        source="myscheme",
    )

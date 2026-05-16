"""Unit tests for myScheme normalizer — no network calls."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))

from scrapers.myscheme.normalizer import normalize

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

PMKISAN_DETAIL: dict = {  # type: ignore[type-arg]
    "_id": "62a70e86f038bd8499a6aa53",
    "slug": "pm-kisan",
    "en": {
        "basicDetails": {
            "schemeName": "Pradhan Mantri Kisan Samman Nidhi",
            "schemeShortTitle": "PM-KISAN",
            "level": {"value": "central", "label": "Central"},
            "state": None,
            "nodalMinistryName": {"value": 498, "label": "Ministry Of Agriculture and Farmers Welfare"},
            "nodalDepartmentName": {"value": 511, "label": "Department of Agriculture"},
            "schemeCategory": [
                {"value": "abc", "label": "Agriculture,Rural & Environment"},
                {"value": "def", "label": "Social welfare & Empowerment"},
            ],
            "tags": ["Farmers", "Income Support"],
        },
        "schemeContent": {
            "detailedDescription_md": "PM-KISAN provides income support to farmers.",
            "briefDescription": "Income support scheme.",
            "benefits_md": "Rs. 6000 per annum per family.",
            "benefitTypes": {"value": "cash", "label": "Cash"},
        },
        "eligibilityCriteria": {
            "eligibilityDescription_md": "All land-holding farmer families.",
        },
        "applicationProcess": [
            {"mode": "Online - via CSC", "url": "https://pmkisan.gov.in/", "process_md": "Step 1..."},
        ],
        "documentsRequired": [],
    },
}

KBIREF_DETAIL: dict = {  # type: ignore[type-arg]
    "_id": "64f75b4a4c841e89deb8e8d8",
    "slug": "k-biref",
    "en": {
        "basicDetails": {
            "schemeName": "Kerala Biotechnology Re-Entry Fellowship",
            "schemeShortTitle": "K-BIREF",
            "level": {"value": "state", "label": "State"},
            "state": {"value": 32, "label": "Kerala"},
            "nodalMinistryName": None,
            "nodalDepartmentName": {"value": 32000040, "label": "Science and Technology Department"},
            "schemeCategory": [{"value": "x", "label": "Education & Learning"}],
            "tags": ["Fellowship", "Research"],
        },
        "schemeContent": {
            "detailedDescription_md": "Fellowship for biotechnology researchers.",
            "briefDescription": "Re-entry fellowship.",
            "benefits_md": "Monthly remuneration of Rs. 1,00,000.",
            "benefitTypes": {"id": 3, "value": "composite", "label": "Composite"},
        },
        "eligibilityCriteria": {
            "eligibilityDescription_md": "Ph.D. with 3 years post-doctoral experience.",
        },
        "applicationProcess": [],
        "documentsRequired": [],
    },
}

LISTING_CENTRAL = {
    "slug": "pm-kisan",
    "beneficiaryState": ["All"],
    "level": "Central",
    "schemeName": "Pradhan Mantri Kisan Samman Nidhi",
}

LISTING_STATE = {
    "slug": "k-biref",
    "beneficiaryState": ["Kerala"],
    "level": "State",
    "schemeName": "Kerala Biotechnology Re-Entry Fellowship",
}

# Karnataka state scheme fixture (based on real KBOCWWB structure)
KBOCWWB_DETAIL: dict = {  # type: ignore[type-arg]
    "_id": "62a70e86f038bd8499a6bb01",
    "slug": "kbocwwb",
    "en": {
        "basicDetails": {
            "schemeName": "Karnataka Building and Other Construction Workers Welfare Board",
            "schemeShortTitle": "KBOCWWB",
            "level": {"value": "state", "label": "State"},
            "state": {"value": 29, "label": "Karnataka"},
            "nodalMinistryName": None,
            "nodalDepartmentName": {"value": 2900010, "label": "Department of Labour"},
            "schemeCategory": [{"value": "lbr", "label": "Labour & Employment"}],
            "tags": ["Construction Workers", "Welfare", "Karnataka"],
        },
        "schemeContent": {
            "detailedDescription_md": "Welfare board for building and construction workers in Karnataka.",
            "briefDescription": "Construction worker welfare.",
            "benefits_md": "Medical, education, and insurance benefits.",
            "benefitTypes": {"value": "composite", "label": "Composite"},
        },
        "eligibilityCriteria": {
            "eligibilityDescription_md": (
                "1. Must be a building/construction worker in Karnataka.\n"
                "2. Age between 18 and 60 years.\n"
                "3. Must have worked for at least 90 days in the preceding 12 months."
            ),
        },
        "applicationProcess": [
            {"mode": "Offline", "url": None, "process_md": "Submit application at the nearest KBOCWWB office."},
        ],
        "documentsRequired": [
            {"documentName": "Aadhaar Card"},
            {"documentName": "Work Certificate"},
        ],
    },
}

LISTING_KARNATAKA = {
    "slug": "kbocwwb",
    "beneficiaryState": ["Karnataka"],
    "level": "State",
    "schemeName": "Karnataka Building and Other Construction Workers Welfare Board",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_central_scheme_basic_fields() -> None:
    scheme = normalize(PMKISAN_DETAIL, LISTING_CENTRAL)
    assert scheme.slug == "pm-kisan"
    assert scheme.name == "Pradhan Mantri Kisan Samman Nidhi"
    assert scheme.level == "central"
    assert scheme.state is None
    assert scheme.ministry == "Ministry Of Agriculture and Farmers Welfare"
    assert scheme.source == "myscheme"
    assert scheme.source_url == "https://www.myscheme.gov.in/schemes/pm-kisan"


def test_central_scheme_benefit_and_eligibility() -> None:
    scheme = normalize(PMKISAN_DETAIL, LISTING_CENTRAL)
    assert scheme.benefit_type == "cash"
    assert scheme.benefit_description == "Rs. 6000 per annum per family."
    assert scheme.raw_eligibility_text == "All land-holding farmer families."


def test_central_scheme_application() -> None:
    scheme = normalize(PMKISAN_DETAIL, LISTING_CENTRAL)
    assert scheme.application_mode == "online"
    assert scheme.application_url == "https://pmkisan.gov.in/"


def test_central_scheme_categories_and_tags() -> None:
    scheme = normalize(PMKISAN_DETAIL, LISTING_CENTRAL)
    assert "Agriculture,Rural & Environment" in scheme.categories
    assert "Social welfare & Empowerment" in scheme.categories
    assert "Farmers" in scheme.tags


def test_state_scheme_level_and_state() -> None:
    scheme = normalize(KBIREF_DETAIL, LISTING_STATE)
    assert scheme.level == "state"
    assert scheme.state == "Kerala"


def test_state_scheme_composite_benefit_maps_to_other() -> None:
    scheme = normalize(KBIREF_DETAIL)
    assert scheme.benefit_type == "other"


def test_ministry_falls_back_to_department() -> None:
    # nodalMinistryName is None → should fall back to nodalDepartmentName
    scheme = normalize(KBIREF_DETAIL)
    assert scheme.ministry == "Science and Technology Department"


def test_no_application_process() -> None:
    scheme = normalize(KBIREF_DETAIL)
    assert scheme.application_url is None
    assert scheme.application_mode is None


def test_listing_fields_supply_state_fallback() -> None:
    detail_no_state = {
        **KBIREF_DETAIL,
        "en": {
            **KBIREF_DETAIL["en"],
            "basicDetails": {**KBIREF_DETAIL["en"]["basicDetails"], "state": None},
        },
    }
    scheme = normalize(detail_no_state, LISTING_STATE)
    assert scheme.state == "Kerala"


@pytest.mark.parametrize(
    ("raw_val", "expected"),
    [
        ("cash", "cash"),
        ("Cash", "cash"),
        ("scholarship", "scholarship"),
        ("pension", "pension"),
        ("composite", "other"),
        ("services", "other"),
        ("goods", "other"),
    ],
)
def test_benefit_type_normalization(raw_val: str, expected: str) -> None:
    detail = {
        **PMKISAN_DETAIL,
        "en": {
            **PMKISAN_DETAIL["en"],
            "schemeContent": {
                **PMKISAN_DETAIL["en"]["schemeContent"],
                "benefitTypes": {"value": raw_val, "label": raw_val.title()},
            },
        },
    }
    scheme = normalize(detail)
    assert scheme.benefit_type == expected


@pytest.mark.parametrize(
    ("mode_str", "expected"),
    [
        ("Online", "online"),
        ("Offline", "offline"),
        ("Online - via CSC", "online"),
        ("Both online and offline", "both"),
        ("Online/Offline", "both"),
        (None, None),
    ],
)
def test_application_mode_normalization(mode_str: str | None, expected: str | None) -> None:
    ap = [{"mode": mode_str, "url": "", "process_md": ""}] if mode_str is not None else []
    detail = {
        **PMKISAN_DETAIL,
        "en": {**PMKISAN_DETAIL["en"], "applicationProcess": ap},
    }
    scheme = normalize(detail)
    assert scheme.application_mode == expected


# ---------------------------------------------------------------------------
# Karnataka state scheme tests
# ---------------------------------------------------------------------------


def test_karnataka_scheme_level_and_state() -> None:
    scheme = normalize(KBOCWWB_DETAIL, LISTING_KARNATAKA)
    assert scheme.level == "state"
    assert scheme.state == "Karnataka"


def test_karnataka_scheme_source_and_url() -> None:
    scheme = normalize(KBOCWWB_DETAIL, LISTING_KARNATAKA)
    assert scheme.source == "myscheme"
    assert scheme.source_url == "https://www.myscheme.gov.in/schemes/kbocwwb"


def test_karnataka_scheme_eligibility_text() -> None:
    scheme = normalize(KBOCWWB_DETAIL, LISTING_KARNATAKA)
    assert scheme.raw_eligibility_text is not None
    assert len(scheme.raw_eligibility_text) > 10
    assert "Karnataka" in scheme.raw_eligibility_text


def test_karnataka_scheme_ministry_falls_back_to_department() -> None:
    scheme = normalize(KBOCWWB_DETAIL, LISTING_KARNATAKA)
    assert scheme.ministry == "Department of Labour"


def test_karnataka_scheme_offline_application() -> None:
    scheme = normalize(KBOCWWB_DETAIL, LISTING_KARNATAKA)
    assert scheme.application_mode == "offline"
    assert scheme.application_url is None


def test_karnataka_scheme_composite_benefit_maps_to_other() -> None:
    scheme = normalize(KBOCWWB_DETAIL, LISTING_KARNATAKA)
    assert scheme.benefit_type == "other"


def test_karnataka_listing_state_fallback() -> None:
    # detail.en.basicDetails.state is None → falls back to listing beneficiaryState
    detail_no_state = {
        **KBOCWWB_DETAIL,
        "en": {
            **KBOCWWB_DETAIL["en"],
            "basicDetails": {**KBOCWWB_DETAIL["en"]["basicDetails"], "state": None},
        },
    }
    scheme = normalize(detail_no_state, LISTING_KARNATAKA)
    assert scheme.state == "Karnataka"


def test_karnataka_documents_required() -> None:
    scheme = normalize(KBOCWWB_DETAIL, LISTING_KARNATAKA)
    assert "Aadhaar Card" in scheme.documents_required
    assert "Work Certificate" in scheme.documents_required

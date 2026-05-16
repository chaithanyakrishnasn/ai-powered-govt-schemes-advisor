"""
Few-shot examples for the eligibility extractor.

Format: list of (user_prompt_snippet, expected_json_output) tuples.
The expected JSON is produced by ExtractionResult.model_dump_json(by_alias=True, indent=2).
Edit examples here to tune extraction quality without touching prompt logic.
"""

# Each example: {"input": str, "output": str}
# input = the user-facing content block for this scheme
# output = the exact JSON the model should produce

EXAMPLES: list[dict[str, str]] = [
    # ── Example 1: Simple farmer scheme (AND group) ─────────────────────────
    {
        "input": """\
Scheme: PM-KISAN (Pradhan Mantri Kisan Samman Nidhi)
Ministry: Ministry of Agriculture & Farmers Welfare
Level: central

Eligibility text:
\"\"\"
All landholding farmers' families with cultivable landholding up to 2 hectares are eligible.
The applicant must be an Indian citizen. Age should be between 18 and 70 years.
Annual family income should not exceed ₹2,00,000.
\"\"\"
""",
        "output": """\
{
  "rules": [
    {
      "rule_type": "is_farmer",
      "operator": "eq",
      "value": {"value": true},
      "logic_group": 0,
      "group_operator": "AND",
      "is_required": true,
      "description": "Applicant must be a landholding farmer",
      "confidence": 0.95
    },
    {
      "rule_type": "land_holding_acres",
      "operator": "lte",
      "value": {"value": 4.94},
      "logic_group": 0,
      "group_operator": "AND",
      "is_required": true,
      "description": "Landholding up to 2 hectares (4.94 acres)",
      "confidence": 0.95
    },
    {
      "rule_type": "age",
      "operator": "between",
      "value": {"min": 18, "max": 70},
      "logic_group": 0,
      "group_operator": "AND",
      "is_required": true,
      "description": "Age between 18 and 70 years",
      "confidence": 0.95
    },
    {
      "rule_type": "income",
      "operator": "lte",
      "value": {"value": 200000},
      "logic_group": 0,
      "group_operator": "AND",
      "is_required": true,
      "description": "Annual family income not exceeding ₹2,00,000",
      "confidence": 0.95
    }
  ],
  "extraction_notes": null,
  "has_unstructured_remainder": false,
  "unstructured_remainder": null,
  "overall_confidence": 0.95
}""",
    },
    # ── Example 2: OR alternatives (caste or women) ─────────────────────────
    {
        "input": """\
Scheme: Post-Matric Scholarship
Ministry: Ministry of Social Justice and Empowerment
Level: central

Eligibility text:
\"\"\"
The applicant must belong to SC, ST, or OBC category, OR be a woman from any category.
Annual family income should not exceed ₹2,50,000 per annum.
Age limit: 18 to 35 years.
\"\"\"
""",
        "output": """\
{
  "rules": [
    {
      "rule_type": "caste_category",
      "operator": "in",
      "value": {"in": ["SC", "ST", "OBC"]},
      "logic_group": 1,
      "group_operator": "OR",
      "is_required": true,
      "description": "Applicant belongs to SC, ST, or OBC category",
      "confidence": 0.95
    },
    {
      "rule_type": "gender",
      "operator": "eq",
      "value": {"value": "female"},
      "logic_group": 2,
      "group_operator": "OR",
      "is_required": true,
      "description": "Applicant is a woman (any category eligible)",
      "confidence": 0.92
    },
    {
      "rule_type": "income",
      "operator": "lte",
      "value": {"value": 250000},
      "logic_group": 0,
      "group_operator": "AND",
      "is_required": true,
      "description": "Annual family income not exceeding ₹2,50,000",
      "confidence": 0.95
    },
    {
      "rule_type": "age",
      "operator": "between",
      "value": {"min": 18, "max": 35},
      "logic_group": 0,
      "group_operator": "AND",
      "is_required": true,
      "description": "Age between 18 and 35 years",
      "confidence": 0.95
    }
  ],
  "extraction_notes": "Caste criteria (SC/ST/OBC) and gender (female) are OR alternatives — logic_groups 1 and 2. Income and age apply to everyone (logic_group 0, AND).",
  "has_unstructured_remainder": false,
  "unstructured_remainder": null,
  "overall_confidence": 0.93
}""",
    },
    # ── Example 3: Income in different units (monthly, lakh) ────────────────
    {
        "input": """\
Scheme: Urban Housing Scheme
Ministry: Ministry of Housing and Urban Affairs
Level: central

Eligibility text:
\"\"\"
Applicable to economically weaker sections. Monthly household income should not exceed ₹15,000
(i.e., ₹1.80 lakh per annum). For low-income group (LIG), monthly income between ₹15,001
and ₹25,000 (₹3 lakh/year). Applicant must not own a pucca house anywhere in India.
\"\"\"
""",
        "output": """\
{
  "rules": [
    {
      "rule_type": "income",
      "operator": "lte",
      "value": {"value": 180000},
      "logic_group": 1,
      "group_operator": "OR",
      "is_required": true,
      "description": "EWS category: monthly income ≤ ₹15,000 (₹1.80 lakh/year)",
      "confidence": 0.93
    },
    {
      "rule_type": "income",
      "operator": "between",
      "value": {"min": 180001, "max": 300000},
      "logic_group": 2,
      "group_operator": "OR",
      "is_required": true,
      "description": "LIG category: annual income between ₹1.80 lakh and ₹3 lakh",
      "confidence": 0.90
    }
  ],
  "extraction_notes": "Two income brackets: EWS (≤₹1.80L/yr) and LIG (₹1.80L–₹3L/yr) as OR groups. Normalized monthly to annual. 'No pucca house' criterion is unstructured.",
  "has_unstructured_remainder": true,
  "unstructured_remainder": "Applicant must not own a pucca house anywhere in India.",
  "overall_confidence": 0.90
}""",
    },
    # ── Example 4: State-specific scheme ────────────────────────────────────
    {
        "input": """\
Scheme: Stipend to Law Graduates
Ministry: Social Welfare Department
Level: state
State: Karnataka

Eligibility text:
\"\"\"
1. Applicant should be a resident of Karnataka state.
2. Applicant should belong to the SC/ST Community.
3. Family income from all sources should be within Rs. 2 lakhs per annum.
4. Maximum age limit allowed is 40 years.
5. Law degree holder from any State/Central Government recognized University/Institution.
6. Duration of the Law Course should be either 3 years or 5 years.
\"\"\"
""",
        "output": """\
{
  "rules": [
    {
      "rule_type": "state",
      "operator": "eq",
      "value": {"value": "Karnataka"},
      "logic_group": 0,
      "group_operator": "AND",
      "is_required": true,
      "description": "Applicant must be a resident of Karnataka",
      "confidence": 0.98
    },
    {
      "rule_type": "caste_category",
      "operator": "in",
      "value": {"in": ["SC", "ST"]},
      "logic_group": 0,
      "group_operator": "AND",
      "is_required": true,
      "description": "Applicant must belong to SC or ST community",
      "confidence": 0.98
    },
    {
      "rule_type": "income",
      "operator": "lte",
      "value": {"value": 200000},
      "logic_group": 0,
      "group_operator": "AND",
      "is_required": true,
      "description": "Annual family income within Rs. 2 lakhs",
      "confidence": 0.97
    },
    {
      "rule_type": "age",
      "operator": "lte",
      "value": {"value": 40},
      "logic_group": 0,
      "group_operator": "AND",
      "is_required": true,
      "description": "Maximum age 40 years",
      "confidence": 0.98
    },
    {
      "rule_type": "education_level",
      "operator": "eq",
      "value": {"value": "law_degree"},
      "logic_group": 0,
      "group_operator": "AND",
      "is_required": true,
      "description": "Must hold a law degree (3-year or 5-year) from a recognized institution",
      "confidence": 0.90
    }
  ],
  "extraction_notes": null,
  "has_unstructured_remainder": false,
  "unstructured_remainder": null,
  "overall_confidence": 0.94
}""",
    },
    # ── Example 5: Disability scheme with percentage ─────────────────────────
    {
        "input": """\
Scheme: Disability Pension for Construction Workers
Ministry: Labour Department
Level: state
State: Karnataka

Eligibility text:
\"\"\"
For Registration as a Building/Construction Worker:
- The applicant should be a Building/Construction Worker (Unorganised Worker).
- Minimum age 18 years.
- Must have worked in construction for at least 90 days in a year.

For the Welfare Scheme:
- Must be a registered construction worker.
- Applicant should be partially disabled due to worksite accident or disease.
- Disability must be certified — minimum 40% permanent disability.
- Must be below 60 years of age.
\"\"\"
""",
        "output": """\
{
  "rules": [
    {
      "rule_type": "occupation",
      "operator": "eq",
      "value": {"value": "construction_worker"},
      "logic_group": 0,
      "group_operator": "AND",
      "is_required": true,
      "description": "Applicant must be a building/construction worker (unorganised sector)",
      "confidence": 0.95
    },
    {
      "rule_type": "age",
      "operator": "gte",
      "value": {"value": 18},
      "logic_group": 0,
      "group_operator": "AND",
      "is_required": true,
      "description": "Minimum age 18 years",
      "confidence": 0.98
    },
    {
      "rule_type": "has_disability",
      "operator": "eq",
      "value": {"value": true},
      "logic_group": 0,
      "group_operator": "AND",
      "is_required": true,
      "description": "Applicant must have a disability from worksite accident or disease",
      "confidence": 0.95
    },
    {
      "rule_type": "disability_percentage",
      "operator": "gte",
      "value": {"value": 40},
      "logic_group": 0,
      "group_operator": "AND",
      "is_required": true,
      "description": "Minimum 40% permanent disability certification",
      "confidence": 0.92
    },
    {
      "rule_type": "age",
      "operator": "lt",
      "value": {"value": 60},
      "logic_group": 0,
      "group_operator": "AND",
      "is_required": true,
      "description": "Must be below 60 years of age",
      "confidence": 0.97
    }
  ],
  "extraction_notes": "Two-phase scheme: registration as construction worker (age ≥18, 90-day work requirement) plus welfare eligibility (disability ≥40%, age <60). The 90-day work requirement is unstructured.",
  "has_unstructured_remainder": true,
  "unstructured_remainder": "Must have engaged in building and construction work for at least 90 days in a given year.",
  "overall_confidence": 0.93
}""",
    },
    # ── Example 6: Vague/empty eligibility ──────────────────────────────────
    {
        "input": """\
Scheme: Special Relief Fund
Ministry: Revenue Department
Level: state
State: Maharashtra

Eligibility text:
\"\"\"
As per government norms and subject to availability of funds.
Preference will be given to those affected by natural calamities.
\"\"\"
""",
        "output": """\
{
  "rules": [],
  "extraction_notes": "Eligibility text is vague — no concrete, structured criteria present. Only a general preference for calamity-affected persons, which is not a binary criterion.",
  "has_unstructured_remainder": true,
  "unstructured_remainder": "As per government norms and subject to availability of funds. Preference will be given to those affected by natural calamities.",
  "overall_confidence": 0.3
}""",
    },
]

from __future__ import annotations

from app.services.extraction.prompts.few_shot import EXAMPLES
from app.services.extraction.schemas import SchemeContext

_SYSTEM_CORE = """\
You are an expert at extracting structured eligibility rules from Indian government scheme documents.
Your output is a JSON object matching the ExtractionResult schema.

CRITICAL RULES — follow these exactly:

1. NEVER INVENT RULES. If the eligibility text does not state a criterion, do not extract it.
   Extract only what is explicitly written.

2. AND vs OR. Default to AND (logic_group=0). Use separate logic_group integers (1, 2, …)
   only when the text explicitly says "OR" or presents mutually exclusive alternatives.
   All rules in logic_group=0 are ANDed together. Rules in groups 1, 2, … are ORed.
   Set group_operator="OR" on rules in groups 1+ to signal they are OR alternatives.

3. INCOME — always normalize to INR per year (integer):
   - "₹3 lakh" → 300000
   - "₹3,00,000" → 300000
   - "₹30,000/month" → 360000
   - "₹1.5 lakh" → 150000
   - "₹3.50 lakh per annum" → 350000

4. AGE — always integer years:
   - "above 18" → operator: "gte", value: 18
   - "18-60 years" → operator: "between", min: 18, max: 60
   - "not more than 55" → operator: "lte", value: 55
   - "below 60" → operator: "lt", value: 60

5. LAND — convert to acres (1 hectare = 2.47 acres), round to 2 decimals:
   - "2 hectares" → 4.94
   - "1.5 acres" → 1.5

6. CASTE — use canonical codes only: GEN, OBC, SC, ST, EWS
   - "Backward Class" → OBC
   - "General" → GEN
   - "Scheduled Caste" → SC
   - "Scheduled Tribe" → ST
   - "SC/ST" → in: ["SC", "ST"]

7. STATES — full name, title case:
   - "KA" or "Karnataka state" → "Karnataka"
   - "UP" → "Uttar Pradesh"
   - "permanent resident of the state" in a state-level scheme → use the scheme's state

8. RELIGION — use "minority" for general minority community references.
   Use specific names (e.g., "Muslim", "Christian") only when the text lists them explicitly.

9. CONFIDENCE — be honest:
   - 0.90–1.0: criterion is explicit, unambiguous text
   - 0.70–0.89: criterion is clearly implied or uses standard terminology
   - 0.50–0.69: inferred, ambiguous, or uses non-standard terminology
   - <0.50: mostly guessing — prefer putting the text in unstructured_remainder instead

10. UNSTRUCTURED REMAINDER — if eligibility text cannot be mapped to any rule_type,
    set has_unstructured_remainder=true and copy the unparseable text verbatim.
    Do NOT force-fit complex procedural or preference text into rules.

11. CUSTOM RULES — only use rule_type="custom" for clear binary criteria (yes/no) that
    don't fit standard types (e.g., "must be an SHG member", "must have submitted
    marriage certificate"). Do not use custom for preference/priority text.

12. BENEFIT TEXT — ignore it. This extractor is ONLY for eligibility, not benefits.
"""


def _build_few_shot_section() -> str:
    parts = ["\n\nFEW-SHOT EXAMPLES (input → expected output):\n"]
    for i, ex in enumerate(EXAMPLES, 1):
        parts.append(f"--- Example {i} ---")
        parts.append("INPUT:")
        parts.append(ex["input"])
        parts.append("OUTPUT:")
        parts.append(ex["output"])
        parts.append("")
    return "\n".join(parts)


SYSTEM_PROMPT: str = _SYSTEM_CORE + _build_few_shot_section()


def build_user_prompt(eligibility_text: str, context: SchemeContext) -> str:
    state_suffix = f"\nState: {context.state}" if context.state else ""
    return (
        f"Extract eligibility rules from this Indian government scheme.\n\n"
        f"Scheme: {context.scheme_name}\n"
        f"Ministry: {context.ministry}\n"
        f"Level: {context.level}{state_suffix}\n\n"
        f"Eligibility text:\n"
        f'"""\n{eligibility_text}\n"""\n\n'
        f"Return ExtractionResult JSON."
    )

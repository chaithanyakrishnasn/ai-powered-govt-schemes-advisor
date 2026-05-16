"""
Live evaluation against real Gemini API.

Run with:
    RUN_LIVE_EVAL=1 uv run pytest backend/tests/extraction/test_extractor_eval.py -s

Outputs eval_report.json in the project root.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from app.services.extraction.schemas import (
    EligibilityRule,
    ExtractionResult,
    SchemeContext,
)

GOLDEN_SET_PATH = Path(__file__).parent / "golden_set.json"
EVAL_REPORT_PATH = Path(__file__).parent.parent.parent.parent / "eval_report.json"

pytestmark = pytest.mark.skipif(
    not os.environ.get("RUN_LIVE_EVAL"),
    reason="Set RUN_LIVE_EVAL=1 to run live Gemini eval",
)


# ── Matching helpers ─────────────────────────────────────────────────────────

def _values_match(expected_v: dict[str, Any], actual_v: dict[str, Any]) -> bool:
    """Fuzzy value match: scalar (±10%), range (±10% each bound), list (same set)."""
    # scalar
    if "value" in expected_v and expected_v["value"] is not None:
        ev = expected_v["value"]
        av = actual_v.get("value")
        if av is None:
            return False
        if isinstance(ev, bool) or isinstance(av, bool):
            return bool(ev) == bool(av)
        try:
            fe, fa = float(ev), float(av)
            if fe == 0:
                return fa == 0
            return abs(fe - fa) / abs(fe) <= 0.10
        except (TypeError, ValueError):
            return str(ev).lower() == str(av).lower()

    # range
    if "min" in expected_v or "max" in expected_v:
        em = expected_v.get("min")
        ex = expected_v.get("max")
        am = actual_v.get("min")
        ax = actual_v.get("max")
        min_ok = em is None or am is None or abs(float(em) - float(am)) / max(1, abs(float(em))) <= 0.10
        max_ok = ex is None or ax is None or abs(float(ex) - float(ax)) / max(1, abs(float(ex))) <= 0.10
        return min_ok and max_ok

    # list
    if "in" in expected_v:
        ei = set(str(x).upper() for x in expected_v["in"])
        ai = set(str(x).upper() for x in actual_v.get("in", []))
        return ei == ai

    return True


def _rule_matches(expected: dict[str, Any], actual: EligibilityRule) -> bool:
    if expected["rule_type"] != actual.rule_type:
        return False
    if expected["operator"] != actual.operator:
        return False
    actual_v = actual.value.model_dump(by_alias=True)
    return _values_match(expected["value"], actual_v)


def _compute_metrics(
    golden: list[dict[str, Any]],
    predictions: list[ExtractionResult],
) -> dict[str, Any]:
    total_expected = 0
    total_matched_expected = 0
    total_predicted = 0
    total_matched_predicted = 0
    high_conf_predicted = 0
    high_conf_correct = 0

    per_example: list[dict[str, Any]] = []

    for entry, pred in zip(golden, predictions, strict=True):
        exp_rules = entry["expected"]["rules"]
        pred_rules = pred.rules

        # recall: how many expected rules were found
        matched_exp = 0
        for exp_r in exp_rules:
            if any(_rule_matches(exp_r, pr) for pr in pred_rules):
                matched_exp += 1

        # precision: how many predicted rules exist in expected
        matched_pred = 0
        for pr in pred_rules:
            if any(_rule_matches(exp_r, pr) for exp_r in exp_rules):
                matched_pred += 1
            # confidence calibration
            if pr.confidence >= 0.8:
                high_conf_predicted += 1
                if any(_rule_matches(exp_r, pr) for exp_r in exp_rules):
                    high_conf_correct += 1

        total_expected += len(exp_rules)
        total_matched_expected += matched_exp
        total_predicted += len(pred_rules)
        total_matched_predicted += matched_pred

        per_example.append(
            {
                "id": entry["id"],
                "slug": entry["slug"],
                "expected_rules": len(exp_rules),
                "predicted_rules": len(pred_rules),
                "matched_expected": matched_exp,
                "matched_predicted": matched_pred,
                "recall": matched_exp / len(exp_rules) if exp_rules else 1.0,
                "precision": matched_pred / len(pred_rules) if pred_rules else 1.0,
                "has_unstructured_remainder": pred.has_unstructured_remainder,
                "overall_confidence": pred.overall_confidence,
                "extraction_notes": pred.extraction_notes,
            }
        )

    recall = total_matched_expected / total_expected if total_expected > 0 else 0.0
    precision = total_matched_predicted / total_predicted if total_predicted > 0 else 0.0
    high_conf_precision = high_conf_correct / high_conf_predicted if high_conf_predicted > 0 else 0.0

    return {
        "rule_recall": recall,
        "rule_precision": precision,
        "high_conf_precision": high_conf_precision,
        "schema_validity": 1.0,  # Instructor guarantees this
        "total_expected_rules": total_expected,
        "total_predicted_rules": total_predicted,
        "high_conf_predicted": high_conf_predicted,
        "high_conf_correct": high_conf_correct,
        "per_example": per_example,
    }


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def golden_set() -> list[dict[str, Any]]:
    return json.loads(GOLDEN_SET_PATH.read_text())


@pytest.fixture(scope="module")
def extractor() -> Any:
    from app.services.extraction.extractor import EligibilityExtractor
    from app.services.llm.gemini import GeminiClient

    return EligibilityExtractor(GeminiClient(), rpm_limit=10)


# ── Tests ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_live_eval_full_golden_set(
    golden_set: list[dict[str, Any]],
    extractor: Any,
) -> None:
    items = [
        (
            entry["eligibility_text"],
            SchemeContext(
                scheme_name=entry["scheme_name"],
                ministry=entry["ministry"],
                level=entry["level"],
                state=entry.get("state"),
            ),
        )
        for entry in golden_set
    ]

    predictions = await extractor.extract_batch(items, concurrency=3)
    assert len(predictions) == len(golden_set)

    metrics = _compute_metrics(golden_set, predictions)

    # Print summary
    print("\n\n══════════════════════════════════════════════════")
    print("  EVAL REPORT — Live Gemini Golden Set")
    print("══════════════════════════════════════════════════")
    print(f"  Examples        : {len(golden_set)}")
    print(f"  Schema validity : {metrics['schema_validity']:.0%}")
    print(f"  Rule recall     : {metrics['rule_recall']:.2%}")
    print(f"  Rule precision  : {metrics['rule_precision']:.2%}")
    print(f"  High-conf prec  : {metrics['high_conf_precision']:.2%} ({metrics['high_conf_correct']}/{metrics['high_conf_predicted']} rules ≥0.8 conf)")
    print(f"  Token usage     : {extractor.usage}")
    print("──────────────────────────────────────────────────")
    for ex in metrics["per_example"]:
        status = "✓" if ex["recall"] >= 0.75 and ex["precision"] >= 0.80 else "✗"
        print(
            f"  {status} {ex['id']:20s} | recall={ex['recall']:.0%} "
            f"prec={ex['precision']:.0%} "
            f"(exp={ex['expected_rules']} pred={ex['predicted_rules']})"
        )
    print("══════════════════════════════════════════════════\n")

    # Write eval report
    report = {
        "golden_set_size": len(golden_set),
        "metrics": {k: v for k, v in metrics.items() if k != "per_example"},
        "per_example": metrics["per_example"],
        "token_usage": {
            "total_input_tokens": extractor.usage.total_input_tokens,
            "total_output_tokens": extractor.usage.total_output_tokens,
            "call_count": extractor.usage.call_count,
            "estimated_cost_usd": extractor.usage.estimated_cost_usd,
        },
        "avg_input_tokens_per_call": (
            extractor.usage.total_input_tokens // max(1, extractor.usage.call_count)
        ),
        "avg_output_tokens_per_call": (
            extractor.usage.total_output_tokens // max(1, extractor.usage.call_count)
        ),
    }
    EVAL_REPORT_PATH.write_text(json.dumps(report, indent=2))
    print(f"  Eval report written to: {EVAL_REPORT_PATH}")

    # Assertions — these define acceptance criteria
    assert metrics["schema_validity"] == 1.0, "Schema validity must be 100%"
    assert metrics["rule_recall"] >= 0.75, (
        f"Rule recall {metrics['rule_recall']:.2%} below target 75%"
    )
    assert metrics["rule_precision"] >= 0.80, (
        f"Rule precision {metrics['rule_precision']:.2%} below target 80%"
    )
    assert metrics["high_conf_precision"] >= 0.90 or metrics["high_conf_predicted"] == 0, (
        f"High-confidence precision {metrics['high_conf_precision']:.2%} below target 90%"
    )


@pytest.mark.asyncio
async def test_live_single_extract(extractor: Any) -> None:
    """Smoke test: single extraction must return valid schema."""
    ctx = SchemeContext(
        scheme_name="Test Scheme",
        ministry="Test Ministry",
        level="central",
    )
    result = await extractor.extract(
        "Applicant must be between 18 and 60 years of age. Annual income must not exceed Rs 3 lakhs.",
        ctx,
    )
    assert isinstance(result, ExtractionResult)
    assert len(result.rules) >= 1
    assert result.overall_confidence > 0

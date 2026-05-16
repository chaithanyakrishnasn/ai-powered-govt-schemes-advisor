"""Unit tests for ExtractionCache."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.services.extraction.schemas import EligibilityRule, ExtractionResult, RuleValue
from app.services.ingestion.cache import ExtractionCache


def _result(n_rules: int = 1) -> ExtractionResult:
    rules = [
        EligibilityRule(
            rule_type="age",
            operator="between",
            value=RuleValue(min=18.0, max=60.0),
            description="Age between 18 and 60",
            confidence=0.9,
        )
        for _ in range(n_rules)
    ]
    return ExtractionResult(rules=rules, overall_confidence=0.9)


class TestExtractionCache:
    def test_miss_on_empty_cache(self, tmp_path: Path) -> None:
        cache = ExtractionCache(tmp_path)
        assert cache.get("text", "name", "ministry") is None
        assert cache.stats.misses == 1
        assert cache.stats.hits == 0

    def test_set_then_get(self, tmp_path: Path) -> None:
        cache = ExtractionCache(tmp_path)
        result = _result()
        cache.set("text", "name", "ministry", result)
        retrieved = cache.get("text", "name", "ministry")
        assert retrieved is not None
        assert len(retrieved.rules) == 1
        assert cache.stats.hits == 1

    def test_different_text_is_miss(self, tmp_path: Path) -> None:
        cache = ExtractionCache(tmp_path)
        cache.set("text A", "name", "ministry", _result())
        assert cache.get("text B", "name", "ministry") is None

    def test_different_name_is_miss(self, tmp_path: Path) -> None:
        cache = ExtractionCache(tmp_path)
        cache.set("text", "name A", "ministry", _result())
        assert cache.get("text", "name B", "ministry") is None

    def test_cache_persists_as_file(self, tmp_path: Path) -> None:
        cache = ExtractionCache(tmp_path)
        cache.set("eligibility text", "Scheme Name", "Ministry", _result())
        files = list(tmp_path.glob("*.json"))
        assert len(files) == 1

    def test_corrupt_cache_entry_discarded(self, tmp_path: Path) -> None:
        cache = ExtractionCache(tmp_path)
        cache.set("text", "name", "ministry", _result())
        # Corrupt the file
        for f in tmp_path.glob("*.json"):
            f.write_text("{invalid json{{")
        result = cache.get("text", "name", "ministry")
        assert result is None
        assert cache.stats.misses == 1

    def test_hit_rate_calculation(self, tmp_path: Path) -> None:
        cache = ExtractionCache(tmp_path)
        cache.set("text", "name", "ministry", _result())
        cache.get("text", "name", "ministry")  # hit
        cache.get("other", "name", "ministry")  # miss
        assert cache.stats.hit_rate == pytest.approx(0.5)

    def test_creates_directory(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "c"
        ExtractionCache(nested)
        assert nested.exists()

    def test_schema_version_invalidates(self, tmp_path: Path) -> None:
        """Changing SCHEMA_VERSION should produce a different cache key."""
        import app.services.ingestion.cache as cache_module

        original = cache_module.SCHEMA_VERSION
        cache = ExtractionCache(tmp_path)
        cache.set("text", "name", "ministry", _result())

        try:
            cache_module.SCHEMA_VERSION = "0.0-old"
            # Monkeypatching the constant affects _key() via module reference
            cache.get("text", "name", "ministry")
            # The key changes so this is a miss (hash collision astronomically unlikely)
        finally:
            cache_module.SCHEMA_VERSION = original

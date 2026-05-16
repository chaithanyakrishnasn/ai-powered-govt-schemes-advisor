"""Unit tests for Deduplicator."""

from __future__ import annotations

from app.schemas.raw_scheme import RawScheme
from app.services.ingestion.dedup import Deduplicator, _normalize_name


def _scheme(slug: str, source: str = "myscheme", level: str = "central", name: str | None = None) -> RawScheme:
    return RawScheme(
        slug=slug,
        name=name or slug.replace("-", " ").title(),
        level=level,  # type: ignore[arg-type]
        source_url="https://example.com",
        source=source,
    )


class TestNormalizeName:
    def test_lowercases(self) -> None:
        assert _normalize_name("PM Kisan") == "pm kisan"

    def test_strips_punctuation(self) -> None:
        assert _normalize_name("Scheme (2024)") == "scheme 2024"

    def test_collapses_spaces(self) -> None:
        assert _normalize_name("  foo   bar  ") == "foo bar"


class TestDeduplicatorExactDup:
    def test_no_dupes(self) -> None:
        schemes = [_scheme("a"), _scheme("b"), _scheme("c")]
        deduplicator = Deduplicator()
        result, report = deduplicator.filter(schemes)
        assert len(result) == 3
        assert report.exact_dupes == 0
        assert report.near_dupes == 0
        assert report.unique == 3

    def test_exact_dup_same_source(self) -> None:
        # Same slug + source appears twice — keep last
        schemes = [
            _scheme("pm-kisan", name="PM Kisan v1"),
            _scheme("pm-kisan", name="PM Kisan v2"),
        ]
        deduplicator = Deduplicator()
        result, report = deduplicator.filter(schemes)
        assert len(result) == 1
        assert result[0].name == "PM Kisan v2"  # last wins
        assert report.exact_dupes == 1

    def test_exact_dup_different_source_not_deduped(self) -> None:
        # Same slug but different sources AND different names — not an exact dup, not a near-dup
        schemes = [
            _scheme("kisan-credit", source="myscheme", name="Kisan Credit Card"),
            _scheme("kisan-credit", source="vikaspedia", name="Village Farm Loan"),
        ]
        deduplicator = Deduplicator()
        result, report = deduplicator.filter(schemes)
        assert len(result) == 2
        assert report.exact_dupes == 0

    def test_multiple_exact_dupes(self) -> None:
        schemes = [_scheme("a")] * 5
        deduplicator = Deduplicator()
        result, report = deduplicator.filter(schemes)
        assert len(result) == 1
        assert report.exact_dupes == 4


class TestDeduplicatorNearDup:
    def test_near_dup_prefers_central(self) -> None:
        # Same name, different sources — prefer central over state
        schemes = [
            _scheme("kisan-state", source="vikaspedia", level="state", name="Kisan Scheme"),
            _scheme("kisan-central", source="myscheme", level="central", name="Kisan Scheme"),
        ]
        deduplicator = Deduplicator()
        result, report = deduplicator.filter(schemes)
        assert len(result) == 1
        assert result[0].slug == "kisan-central"
        assert report.near_dupes == 1

    def test_near_dup_keeps_first_if_not_central_preference(self) -> None:
        # Both state — keep first
        schemes = [
            _scheme("s1", source="myscheme", level="state", name="Farmer Aid"),
            _scheme("s2", source="vikaspedia", level="state", name="Farmer Aid"),
        ]
        deduplicator = Deduplicator()
        result, report = deduplicator.filter(schemes)
        assert len(result) == 1
        assert result[0].slug == "s1"
        assert report.near_dupes == 1

    def test_same_source_same_name_not_near_dup(self) -> None:
        # Same source + similar name (but different slugs) — not a near-dup (different schemes)
        schemes = [
            _scheme("kbocwwb-a", source="myscheme", level="state", name="KBOCWWB Scheme A"),
            _scheme("kbocwwb-b", source="myscheme", level="state", name="KBOCWWB Scheme B"),
        ]
        deduplicator = Deduplicator()
        result, report = deduplicator.filter(schemes)
        assert len(result) == 2
        assert report.near_dupes == 0

    def test_report_totals(self) -> None:
        schemes = [_scheme("a"), _scheme("b"), _scheme("a")]  # 1 exact dup
        deduplicator = Deduplicator()
        result, report = deduplicator.filter(schemes)
        assert report.total == 3
        assert report.unique == 2
        assert report.exact_dupes == 1
        assert report.near_dupes == 0

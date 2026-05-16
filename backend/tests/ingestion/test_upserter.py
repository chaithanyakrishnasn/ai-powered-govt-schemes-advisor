"""Unit tests for SchemeUpserter (mocked AsyncSession)."""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.db.models import EligibilityRule as DBEligibilityRule
from app.db.models import Scheme as DBScheme
from app.services.ingestion.upserter import SchemeUpserter, UpsertResult


def _scheme(slug: str = "test-slug") -> DBScheme:
    s = DBScheme(
        slug=slug,
        name="Test Scheme",
        level="central",
        source_url="https://example.com",
        source="myscheme",
        categories=[],
        documents_required=[],
    )
    return s


def _rule() -> DBEligibilityRule:
    return DBEligibilityRule(
        rule_type="age",
        operator="between",
        value={"min": 18.0, "max": 60.0},
        logic_group=0,
        group_operator="AND",
        is_required=True,
        description="Age between 18 and 60",
        confidence=Decimal("0.9"),
    )


def _make_mock_session(scheme_id: int = 1, xmax: int = 0) -> MagicMock:
    """Return a mock AsyncSession that simulates a successful insert (xmax=0)."""
    session = MagicMock()

    # The context manager for session.begin()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=None)
    cm.__aexit__ = AsyncMock(return_value=False)
    session.begin.return_value = cm

    # execute() returns a row with (id, xmax)
    execute_result = MagicMock()
    execute_result.one.return_value = (scheme_id, xmax)
    session.execute = AsyncMock(return_value=execute_result)

    session.add = MagicMock()
    return session


class TestUpsertResult:
    def test_inserted_action(self) -> None:
        r = UpsertResult(slug="test", action="inserted", rules_count=3)
        assert r.action == "inserted"
        assert r.rules_count == 3
        assert r.error is None

    def test_failed_action(self) -> None:
        r = UpsertResult(slug="test", action="failed", error="DB error")
        assert r.action == "failed"
        assert r.error == "DB error"


class TestSchemeUpserterMocked:
    @pytest.mark.asyncio
    async def test_upsert_insert_action(self) -> None:
        session = _make_mock_session(scheme_id=42, xmax=0)
        upserter = SchemeUpserter(session)  # type: ignore[arg-type]
        result = await upserter.upsert(_scheme(), [_rule()])
        assert result.action == "inserted"
        assert result.rules_count == 1
        assert result.slug == "test-slug"

    @pytest.mark.asyncio
    async def test_upsert_update_action(self) -> None:
        # xmax > 0 → existing row was updated
        session = _make_mock_session(scheme_id=7, xmax=999)
        upserter = SchemeUpserter(session)  # type: ignore[arg-type]
        result = await upserter.upsert(_scheme(), [])
        assert result.action == "updated"
        assert result.rules_count == 0

    @pytest.mark.asyncio
    async def test_upsert_exception_returns_failed(self) -> None:
        session = MagicMock()
        cm = AsyncMock()
        cm.__aenter__ = AsyncMock(side_effect=RuntimeError("connection lost"))
        cm.__aexit__ = AsyncMock(return_value=False)
        session.begin.return_value = cm

        upserter = SchemeUpserter(session)  # type: ignore[arg-type]
        result = await upserter.upsert(_scheme(), [])
        assert result.action == "failed"
        assert result.error is not None
        assert "connection lost" in result.error

    @pytest.mark.asyncio
    async def test_upsert_adds_rules_to_session(self) -> None:
        session = _make_mock_session(scheme_id=10, xmax=0)
        upserter = SchemeUpserter(session)  # type: ignore[arg-type]
        rules = [_rule(), _rule()]
        await upserter.upsert(_scheme(), rules)
        # session.add should be called once per rule
        assert session.add.call_count == len(rules)

    @pytest.mark.asyncio
    async def test_upsert_sets_scheme_id_on_rules(self) -> None:
        session = _make_mock_session(scheme_id=55, xmax=0)
        upserter = SchemeUpserter(session)  # type: ignore[arg-type]
        rule = _rule()
        await upserter.upsert(_scheme(), [rule])
        assert rule.scheme_id == 55

    @pytest.mark.asyncio
    async def test_dry_run_is_not_responsibility_of_upserter(self) -> None:
        # Dry-run is enforced at the pipeline level, not the upserter.
        # This test documents that: calling upsert() on a real session would write.
        # We just verify no assertion errors here.
        session = _make_mock_session()
        upserter = SchemeUpserter(session)  # type: ignore[arg-type]
        result = await upserter.upsert(_scheme(), [])
        assert result.action in ("inserted", "updated", "failed")

"""Integration tests for SemanticRetriever using a real test DB with seeded embeddings."""

from __future__ import annotations

import math
import os
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.services.embedding.embedder import GeminiEmbedder
from app.services.embedding.retriever import SchemeFilters, SemanticRetriever

_TEST_DB_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://user:password@localhost:5432/yojana",
)

pytestmark = pytest.mark.skipif(
    "CI" not in os.environ and not os.environ.get("RUN_DB_TESTS"),
    reason="Set RUN_DB_TESTS=1 to run DB integration tests",
)


def _unit_vec(hot_dim: int, total: int = 768) -> list[float]:
    """One-hot unit vector at dimension `hot_dim`."""
    v = [0.0] * total
    v[hot_dim] = 1.0
    return v


def _embed_mock(return_vec: list[float]) -> GeminiEmbedder:
    mock_client = MagicMock()
    resp = MagicMock()
    resp.embeddings = [MagicMock(values=return_vec)]
    mock_client.raw_client.aio.models.embed_content = AsyncMock(return_value=resp)
    return GeminiEmbedder(mock_client)


@pytest_asyncio.fixture(scope="module")
async def db_session() -> AsyncSession:  # type: ignore[misc]
    engine = create_async_engine(_TEST_DB_URL, echo=False)
    maker = async_sessionmaker(engine, expire_on_commit=False)

    # Seed 5 deterministic schemes with distinct one-hot embeddings
    # Dim 0 → farmers; Dim 1 → women; Dim 2 → disability; Dim 3 → education; Dim 4 → pension
    seed_schemes = [
        {
            "slug": "_test_farmer_scheme",
            "name": "Test Farmer Scheme",
            "level": "central",
            "state": None,
            "categories": ["agriculture"],
            "embedding": _unit_vec(0),
            "search_text": "Farmers land agricultural subsidy",
            "source": "test",
            "source_url": "https://test.example",
        },
        {
            "slug": "_test_women_scheme",
            "name": "Test Women Empowerment Scheme",
            "level": "state",
            "state": "Karnataka",
            "categories": ["women and child"],
            "embedding": _unit_vec(1),
            "search_text": "Women empowerment skill development Karnataka",
            "source": "test",
            "source_url": "https://test.example",
        },
        {
            "slug": "_test_disability_scheme",
            "name": "Test Disability Assistance Scheme",
            "level": "central",
            "state": None,
            "categories": ["social welfare & empowerment"],
            "embedding": _unit_vec(2),
            "search_text": "Persons with disabilities PwD assistance",
            "source": "test",
            "source_url": "https://test.example",
        },
        {
            "slug": "_test_education_scheme",
            "name": "Test Scholarship Education Scheme",
            "level": "central",
            "state": None,
            "categories": ["education & learning"],
            "embedding": _unit_vec(3),
            "search_text": "Scholarship education SC ST students",
            "source": "test",
            "source_url": "https://test.example",
        },
        {
            "slug": "_test_pension_scheme",
            "name": "Test Old Age Pension Scheme",
            "level": "state",
            "state": "Karnataka",
            "categories": ["social welfare & empowerment"],
            "embedding": _unit_vec(4),
            "search_text": "Pension old age elderly social welfare",
            "source": "test",
            "source_url": "https://test.example",
        },
    ]

    async with maker() as session, session.begin():
        # Clean up any previous test seeds
        await session.execute(
            text("DELETE FROM schemes WHERE slug LIKE '_test_%'")
        )
        for s in seed_schemes:
            vec_str = "[" + ",".join(str(v) for v in s["embedding"]) + "]"
            await session.execute(
                text("""
                        INSERT INTO schemes
                            (slug, name, level, state, categories, embedding, search_text,
                             source, source_url, is_active)
                        VALUES
                            (:slug, :name, :level, :state, :categories, :vec::vector,
                             :search_text, :source, :source_url, true)
                        ON CONFLICT (slug) DO UPDATE SET
                            embedding = EXCLUDED.embedding,
                            search_text = EXCLUDED.search_text
                    """),
                {
                    "slug": s["slug"],
                    "name": s["name"],
                    "level": s["level"],
                    "state": s["state"],
                    "categories": s["categories"],
                    "vec": vec_str,
                    "search_text": s["search_text"],
                    "source": s["source"],
                    "source_url": s["source_url"],
                },
            )

    async with maker() as session:
        yield session

    # Teardown
    async with maker() as session, session.begin():
        await session.execute(
            text("DELETE FROM schemes WHERE slug LIKE '_test_%'")
        )
    await engine.dispose()


class TestSemanticRetriever:
    @pytest.mark.asyncio
    async def test_returns_correct_top_result_by_embedding(
        self, db_session: AsyncSession
    ) -> None:
        # Query with unit vec pointing at dim 0 → should return _test_farmer_scheme first
        embedder = _embed_mock(_unit_vec(0))
        retriever = SemanticRetriever(db_session, embedder)
        results = await retriever.search("farmers", top_k=5, min_similarity=0.0)

        farmer_slugs = [r.slug for r in results]
        assert "_test_farmer_scheme" in farmer_slugs
        # Farmer scheme should rank first (exact embedding match)
        assert results[0].slug == "_test_farmer_scheme"
        assert results[0].similarity > 0.99

    @pytest.mark.asyncio
    async def test_filter_by_level_central(self, db_session: AsyncSession) -> None:
        # Dim 1 is a state-level scheme; querying with dim 1 + level=central should exclude it
        embedder = _embed_mock(_unit_vec(1))
        retriever = SemanticRetriever(db_session, embedder)
        filters = SchemeFilters(level="central")
        results = await retriever.search("women", top_k=5, min_similarity=0.0, filters=filters)

        slugs = [r.slug for r in results]
        # _test_women_scheme is state-level; should not appear
        assert "_test_women_scheme" not in slugs

    @pytest.mark.asyncio
    async def test_filter_by_state(self, db_session: AsyncSession) -> None:
        embedder = _embed_mock(_unit_vec(4))
        retriever = SemanticRetriever(db_session, embedder)
        filters = SchemeFilters(state="Karnataka")
        results = await retriever.search("pension", top_k=5, min_similarity=0.0, filters=filters)

        slugs = [r.slug for r in results]
        assert "_test_pension_scheme" in slugs
        # Central scheme with no state should not appear
        assert "_test_disability_scheme" not in slugs

    @pytest.mark.asyncio
    async def test_min_similarity_cutoff(self, db_session: AsyncSession) -> None:
        # Use a diagonal vector that's orthogonal to all test embeddings
        # cos_sim = 0 for orthogonal vectors; with high min_similarity, returns nothing
        diag = [1.0 / math.sqrt(768)] * 768  # uniform vector, low sim to all one-hots
        embedder = _embed_mock(diag)
        retriever = SemanticRetriever(db_session, embedder)
        results = await retriever.search("query", top_k=5, min_similarity=0.99)

        # uniform vector has ~0.036 cosine similarity to unit vec, well below 0.99
        for r in results:
            assert r.slug not in [
                "_test_farmer_scheme",
                "_test_women_scheme",
                "_test_disability_scheme",
                "_test_education_scheme",
                "_test_pension_scheme",
            ]

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty(self, db_session: AsyncSession) -> None:
        embedder = _embed_mock(_unit_vec(0))
        retriever = SemanticRetriever(db_session, embedder)
        results = await retriever.search("  ", top_k=5)
        assert results == []

    @pytest.mark.asyncio
    async def test_result_fields_populated(self, db_session: AsyncSession) -> None:
        embedder = _embed_mock(_unit_vec(0))
        retriever = SemanticRetriever(db_session, embedder)
        results = await retriever.search("test", top_k=5, min_similarity=0.0)

        assert len(results) > 0
        r = results[0]
        assert r.scheme_id > 0
        assert r.slug != ""
        assert r.name != ""
        assert r.level in ("central", "state")
        assert isinstance(r.categories, list)
        assert 0.0 <= r.similarity <= 1.0

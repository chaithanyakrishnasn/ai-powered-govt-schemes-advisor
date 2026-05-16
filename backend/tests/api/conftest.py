"""Fixtures for API tests."""

import asyncio
from collections.abc import AsyncGenerator, Generator, Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from asgi_lifespan import LifespanManager
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.deps import get_db, get_matching_service
from app.db import session as db_session_module
from app.db.base import Base
from app.main import app
from app.services.matching.scheme_matcher import EligibilityStatus, SchemeMatchResult

# Use the test database service from docker-compose
TEST_DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5433/test_yojana"
engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
db_session_module.engine = engine
db_session_module.async_session_maker = async_session_maker


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database() -> AsyncGenerator[None, None]:
    """Create the database tables before the test session."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        await conn.execute(
            insert(Base.metadata.tables["schemes"]),
            [
                {
                    "id": 100_000 + idx,
                    "slug": f"_health_seed_{idx}",
                    "name": f"Health Seed Scheme {idx}",
                    "level": "central",
                    "categories": ["seed"],
                    "search_text": "seed scheme",
                    "source_url": "https://example.com/seed",
                    "source": "test",
                }
                for idx in range(301)
            ],
        )
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
def mock_matching_service() -> MagicMock:
    """Mock MatchingService for tests that don't need real matching logic."""
    mock_service = MagicMock()
    mock_results = [
        SchemeMatchResult(
            scheme_id=1,
            slug="pm-kisan",
            name="PM Kisan",
            status=EligibilityStatus.ELIGIBLE,
            score=0.95,
            rule_evaluations=[],
            missing_fields=[],
            failed_rules=[],
        )
    ]
    # The service returns a tuple of (results, candidates, explanations)
    mock_service.match_profile = AsyncMock(
        return_value=(mock_results, mock_results, None)
    )
    return mock_service


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield a new session with a transaction that is rolled back after the test."""
    async with engine.connect() as connection:
        transaction = await connection.begin()
        maker = async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        async with maker() as session:
            yield session
        await transaction.rollback()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession, mock_matching_service: MagicMock
) -> AsyncGenerator[AsyncClient, None]:
    """
    Yield a test client that uses the transactional session and has services mocked.
    """

    def override_get_db() -> Generator[AsyncSession, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_matching_service] = lambda: mock_matching_service

    async with LifespanManager(app), AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_matching_service, None)

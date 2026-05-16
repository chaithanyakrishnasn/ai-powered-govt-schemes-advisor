"""Tests for the /api/v1/schemes endpoints."""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Scheme

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
async def populate_schemes(db_session: AsyncSession):
    """Fixture to populate the DB with some test schemes for querying."""
    schemes = [
        Scheme(
            slug="pm-kisan",
            name="PM-KISAN",
            level="central",
            categories=["agriculture", "farmer"],
            search_text="farmer aid",
            source_url="http://example.com/pmkisan",
            source="test"
        ),
        Scheme(
            slug="karnataka-scholarship",
            name="Karnataka State Scholarship",
            level="state",
            state="Karnataka",
            categories=["education", "student"],
            search_text="student scholarship",
            source_url="http://example.com/ksp",
            source="test"
        ),
        Scheme(
            slug="generic-central-scheme",
            name="Generic Central Scheme",
            level="central",
            categories=["general"],
            search_text="generic central",
            source_url="http://example.com/gcs",
            source="test"
        ),
    ]
    db_session.add_all(schemes)
    await db_session.commit()
    yield
    # Teardown: delete all schemes
    for s in schemes:
        await db_session.delete(s)
    await db_session.commit()



async def test_get_schemes_paginated(client: AsyncClient):
    """Test basic paginated listing of schemes."""
    response = await client.get("/api/v1/schemes?page=1&size=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 3
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["size"] == 2


async def test_filter_schemes_by_level(client: AsyncClient):
    """Test filtering schemes by level."""
    response = await client.get("/api/v1/schemes?level=central")
    assert response.status_code == 200
    data = response.json()
    assert all(item["level"] == "central" for item in data["items"])
    assert len(data["items"]) >= 2


async def test_filter_schemes_by_state(client: AsyncClient):
    """Test filtering schemes by state."""
    response = await client.get("/api/v1/schemes?state=Karnataka")
    assert response.status_code == 200
    data = response.json()
    assert all(item["state"] == "Karnataka" for item in data["items"])
    assert len(data["items"]) == 1
    assert data["items"][0]["slug"] == "karnataka-scholarship"


async def test_search_schemes_by_query(client: AsyncClient):
    """Test full-text search for schemes."""
    response = await client.get("/api/v1/schemes?q=farmer")
    assert response.status_code == 200
    data = response.json()
    assert len(data["items"]) >= 1
    assert "pm-kisan" in [item["slug"] for item in data["items"]]


async def test_get_scheme_details(client: AsyncClient):
    """Test retrieving full details for a single scheme."""
    response = await client.get("/api/v1/schemes/pm-kisan")
    assert response.status_code == 200
    data = response.json()
    assert data["slug"] == "pm-kisan"
    assert "eligibility_rules" in data
    assert isinstance(data["eligibility_rules"], list)


async def test_get_nonexistent_scheme(client: AsyncClient):
    """Test retrieving a scheme that does not exist."""
    response = await client.get("/api/v1/schemes/nonexistent-scheme")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"
    assert response.json()["resource"] == "scheme"

"""Tests for the /api/v1/profiles endpoints."""
import uuid

import pytest
from httpx import AsyncClient

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


async def test_create_profile_empty(client: AsyncClient):
    """Test creating a profile with no data."""
    response = await client.post("/api/v1/profiles/", json={})
    assert response.status_code == 201
    data = response.json()
    assert "profile_id" in data
    assert "created_at" in data
    assert data["field_count"] == 0


async def test_create_and_get_profile(client: AsyncClient):
    """Test creating a profile and then retrieving it."""
    profile_data = {"age": 35, "state": "Karnataka", "occupation": "farmer"}
    create_response = await client.post("/api/v1/profiles/", json=profile_data)
    assert create_response.status_code == 201
    created_data = create_response.json()
    profile_id = created_data["profile_id"]

    get_response = await client.get(f"/api/v1/profiles/{profile_id}")
    assert get_response.status_code == 200
    retrieved_data = get_response.json()
    assert retrieved_data["id"] == profile_id
    assert retrieved_data["age"] == 35
    assert retrieved_data["state"] == "Karnataka"


async def test_get_missing_profile(client: AsyncClient):
    """Test getting a profile that doesn't exist."""
    random_id = uuid.uuid4()
    response = await client.get(f"/api/v1/profiles/{random_id}")
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


async def test_patch_profile(client: AsyncClient):
    """Test partially updating a profile."""
    profile_data = {"age": 35, "state": "Karnataka", "occupation": "farmer"}
    create_response = await client.post("/api/v1/profiles/", json=profile_data)
    profile_id = create_response.json()["profile_id"]

    patch_data = {"age": 36, "occupation": "software_engineer"}
    patch_response = await client.patch(f"/api/v1/profiles/{profile_id}", json=patch_data)
    assert patch_response.status_code == 200
    updated_data = patch_response.json()
    assert updated_data["age"] == 36
    assert updated_data["occupation"] == "software_engineer"
    assert updated_data["state"] == "Karnataka"  # Should be unchanged


async def test_patch_missing_profile(client: AsyncClient):
    """Test patching a profile that doesn't exist."""
    random_id = uuid.uuid4()
    response = await client.patch(f"/api/v1/profiles/{random_id}", json={"age": 40})
    assert response.status_code == 404
    assert response.json()["error"] == "not_found"


async def test_profile_round_trip(client: AsyncClient):
    """Test full create and retrieve with all field types."""
    full_profile = {
        "age": 42,
        "gender": "female",
        "state": "Tamil Nadu",
        "annual_income": 120000.50,
        "is_farmer": True,
        "has_disability": False,
    }
    create_response = await client.post("/api/v1/profiles/", json=full_profile)
    assert create_response.status_code == 201
    profile_id = create_response.json()["profile_id"]

    get_response = await client.get(f"/api/v1/profiles/{profile_id}")
    assert get_response.status_code == 200
    retrieved_data = get_response.json()
    assert retrieved_data["age"] == full_profile["age"]
    assert retrieved_data["gender"] == full_profile["gender"]
    assert retrieved_data["annual_income"] == full_profile["annual_income"]
    assert retrieved_data["is_farmer"] == full_profile["is_farmer"]

"""Tests for the /api/v1/match endpoint."""

import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import AsyncClient

from app.api.deps import get_matching_service
from app.main import app
from app.schemas.user_profile import UserProfile as UserProfileSchema
from app.services.matching.llm_reranker import SchemeExplanation
from app.services.matching.scheme_matcher import EligibilityStatus, SchemeMatchResult

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_matching_service() -> Generator[MagicMock, None, None]:
    """Fixture to mock the MatchingService."""
    mock = MagicMock()
    mock.match_profile = AsyncMock()

    # Default mock behavior
    mock.match_profile.return_value = (
        [
            SchemeMatchResult(
                scheme_id=1,
                slug="test-scheme",
                name="Test Scheme",
                status=EligibilityStatus.ELIGIBLE,
                score=0.9,
                rule_evaluations=[],
            )
        ],
        [MagicMock()],  # candidates
        None,  # explanations
    )

    app.dependency_overrides[get_matching_service] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_matching_service, None)


@pytest.fixture
async def test_profile(client: AsyncClient) -> UserProfileSchema:
    """Fixture to create a user profile for testing."""
    profile_data = {"age": 30, "state": "Test State"}
    response = await client.post("/api/v1/profiles/", json=profile_data)
    assert response.status_code == 201
    profile_id = response.json()["profile_id"]
    get_response = await client.get(f"/api/v1/profiles/{profile_id}")
    return UserProfileSchema.model_validate(get_response.json())


async def test_match_with_inline_profile(
    client: AsyncClient, mock_matching_service: MagicMock
) -> None:
    """Test matching with an inline profile. A new profile should be created."""
    request_data = {"profile": {"age": 40, "occupation": "worker"}}
    response = await client.post("/api/v1/match/", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert "profile_id" in data
    assert data["total_candidates"] > 0
    assert len(data["results"]) > 0
    mock_matching_service.match_profile.assert_called_once()


async def test_match_with_profile_id(
    client: AsyncClient,
    mock_matching_service: MagicMock,
    test_profile: UserProfileSchema,
) -> None:
    """Test matching using an existing profile ID."""
    request_data = {"profile_id": str(test_profile.id)}
    response = await client.post("/api/v1/match/", json=request_data)
    assert response.status_code == 200
    mock_matching_service.match_profile.assert_called_once()
    # Check that the profile passed to the service has the correct ID
    call_args = mock_matching_service.match_profile.call_args
    assert call_args.kwargs["profile"].id == test_profile.id


async def test_match_no_profile_fails(client: AsyncClient) -> None:
    """Test that a match request with neither profile nor profile_id fails."""
    response = await client.post("/api/v1/match/", json={"query": "some query"})
    assert response.status_code == 422  # Unprocessable Entity


async def test_match_bad_profile_id_fails(client: AsyncClient) -> None:
    """Test that a match request with a non-existent profile_id fails."""
    random_id = uuid.uuid4()
    response = await client.post("/api/v1/match/", json={"profile_id": str(random_id)})
    assert response.status_code == 404


async def test_match_explain_false(
    client: AsyncClient,
    mock_matching_service: MagicMock,
    test_profile: UserProfileSchema,
) -> None:
    """Test that explanations are None when explain=False."""
    request_data = {"profile_id": str(test_profile.id), "explain": False}
    response = await client.post("/api/v1/match/", json=request_data)
    assert response.status_code == 200
    assert response.json()["explanations"] is None
    mock_matching_service.match_profile.assert_called_with(
        profile=test_profile,
        query=None,
        max_results=20,
        include_ineligible=False,
        explain=False,
        language="en",
    )


async def test_match_explain_true(
    client: AsyncClient,
    mock_matching_service: MagicMock,
    test_profile: UserProfileSchema,
) -> None:
    """Test that explanations are returned when explain=True."""
    # Setup mock to return explanations
    mock_explanations = [
        SchemeExplanation(
            scheme_id=1,
            slug="test-scheme",
            name="Test Scheme",
            final_rank=1,
            eligibility_verdict="eligible",
            confidence=0.95,
            explanation="Matches well.",
            key_benefits=[],
            action_steps=[],
            missing_info=[],
        )
    ]
    mock_matching_service.match_profile.return_value = (
        mock_matching_service.match_profile.return_value[0],
        mock_matching_service.match_profile.return_value[1],
        mock_explanations,
    )

    request_data = {"profile_id": str(test_profile.id), "explain": True}
    response = await client.post("/api/v1/match/", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert data["explanations"] is not None
    assert len(data["explanations"]) == 1
    assert data["explanations"][0]["slug"] == "test-scheme"


async def test_match_response_contains_stats(
    client: AsyncClient, test_profile: UserProfileSchema
) -> None:
    """Test that the match response includes pipeline stats."""
    request_data = {"profile_id": str(test_profile.id)}
    response = await client.post("/api/v1/match/", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert "pipeline_stats" in data
    stats = data["pipeline_stats"]
    assert "stage1_candidates" in stats
    assert "total_latency_ms" in stats
    assert stats["stage1_candidates"] > 0

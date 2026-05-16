from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_db
from app.main import app


@pytest.mark.asyncio
async def test_health_check_ok(client: AsyncClient):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["db"] == "connected"
    assert data["schemes_count"] > 300
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_health_check_db_error():
    """
    This test manages its own client to avoid fixture conflicts
    when modifying app.dependency_overrides.
    """
    mock_session = AsyncMock()
    mock_session.scalar.side_effect = Exception("DB connection error")

    async def mock_get_db_error():
        yield mock_session

    app.dependency_overrides[get_db] = mock_get_db_error

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        response = await c.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["db"] == "error"
        assert data["schemes_count"] == -1

    # cleanup
    del app.dependency_overrides[get_db]


@pytest.mark.asyncio
async def test_not_found_handler(client: AsyncClient):
    response = await client.get("/api/v1/nonexistent-path")
    assert response.status_code == 404
    data = response.json()
    assert data["error"] == "http_error"
    assert data["message"] == "Not Found"
    assert "request_id" in data


@pytest.mark.asyncio
async def test_request_id_header(client: AsyncClient):
    response1 = await client.get("/api/v1/health")
    response2 = await client.get("/api/v1/health")

    assert "X-Request-ID" in response1.headers
    assert "X-Request-ID" in response2.headers
    assert response1.headers["X-Request-ID"] != response2.headers["X-Request-ID"]

    custom_request_id = "my-custom-request-id"
    response3 = await client.get("/api/v1/health", headers={"X-Request-ID": custom_request_id})
    assert response3.headers["X-Request-ID"] == custom_request_id


import pytest
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_health_all_healthy(async_client):
    with patch("app.api.routes._check_redis", AsyncMock(return_value="healthy")), \
         patch("app.api.routes._check_celery", AsyncMock(return_value="healthy")), \
         patch("app.api.routes._check_db", AsyncMock(return_value="healthy")):
        response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["checks"]["redis"] == "healthy"
    assert data["checks"]["celery"] == "healthy"
    assert data["checks"]["db"] == "healthy"


@pytest.mark.asyncio
async def test_health_redis_down_is_degraded(async_client):
    with patch("app.api.routes._check_redis", AsyncMock(return_value="unavailable")), \
         patch("app.api.routes._check_celery", AsyncMock(return_value="healthy")), \
         patch("app.api.routes._check_db", AsyncMock(return_value="healthy")):
        response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["redis"] == "unavailable"


@pytest.mark.asyncio
async def test_health_celery_down_is_degraded(async_client):
    with patch("app.api.routes._check_redis", AsyncMock(return_value="healthy")), \
         patch("app.api.routes._check_celery", AsyncMock(return_value="unavailable")), \
         patch("app.api.routes._check_db", AsyncMock(return_value="healthy")):
        response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["checks"]["celery"] == "unavailable"


@pytest.mark.asyncio
async def test_health_db_down_is_unhealthy(async_client):
    with patch("app.api.routes._check_redis", AsyncMock(return_value="healthy")), \
         patch("app.api.routes._check_celery", AsyncMock(return_value="healthy")), \
         patch("app.api.routes._check_db", AsyncMock(return_value="unhealthy")):
        response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["checks"]["db"] == "unhealthy"

import pytest


@pytest.mark.asyncio
async def test_metrics_returns_200(async_client):
    response = await async_client.get("/metrics")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_metrics_content_type_is_prometheus(async_client):
    response = await async_client.get("/metrics")
    assert "text/plain" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_metrics_contains_expected_names(async_client):
    response = await async_client.get("/metrics")
    body = response.text
    assert "scraper_requests_total" in body
    assert "scraper_request_duration_seconds" in body
    assert "scraper_cache_hits_total" in body
    assert "scraper_cache_misses_total" in body
    assert "scraper_queue_depth" in body


@pytest.mark.asyncio
async def test_metrics_repeatable(async_client):
    r1 = await async_client.get("/metrics")
    r2 = await async_client.get("/metrics")
    assert r1.status_code == 200
    assert r2.status_code == 200
    # Both responses contain the same metric names
    assert "scraper_requests_total" in r1.text
    assert "scraper_requests_total" in r2.text

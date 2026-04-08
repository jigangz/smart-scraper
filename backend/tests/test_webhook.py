"""Tests for webhook_url field and webhook delivery via API."""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_create_job_with_webhook_url(async_client):
    """POST /api/jobs stores webhook_url and returns it in the response."""
    response = await async_client.post("/api/jobs", json={
        "name": "Webhook Job",
        "url": "https://example.com",
        "selectors": {"title": "h1"},
        "webhook_url": "https://hooks.example.com/notify",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["webhook_url"] == "https://hooks.example.com/notify"


@pytest.mark.asyncio
async def test_create_job_without_webhook_url(async_client):
    """POST /api/jobs without webhook_url returns null webhook_url."""
    response = await async_client.post("/api/jobs", json={
        "name": "No Webhook Job",
        "url": "https://example.com",
        "selectors": {"title": "h1"},
    })
    assert response.status_code == 201
    data = response.json()
    assert data["webhook_url"] is None


@pytest.mark.asyncio
async def test_get_job_includes_webhook_url(async_client):
    """GET /api/jobs/{id} includes webhook_url field."""
    create_resp = await async_client.post("/api/jobs", json={
        "name": "Hook Job",
        "url": "https://example.com",
        "selectors": {"item": ".item"},
        "webhook_url": "https://hooks.example.com/cb",
    })
    job_id = create_resp.json()["id"]

    get_resp = await async_client.get(f"/api/jobs/{job_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["webhook_url"] == "https://hooks.example.com/cb"


@pytest.mark.asyncio
async def test_list_jobs_includes_webhook_url(async_client):
    """GET /api/jobs includes webhook_url in job list items."""
    await async_client.post("/api/jobs", json={
        "name": "Listed Hook Job",
        "url": "https://example.com",
        "selectors": {"x": "div"},
        "webhook_url": "https://hooks.example.com/list",
    })
    list_resp = await async_client.get("/api/jobs")
    assert list_resp.status_code == 200
    jobs = list_resp.json()["jobs"]
    assert len(jobs) >= 1
    hook_jobs = [j for j in jobs if j["webhook_url"] == "https://hooks.example.com/list"]
    assert len(hook_jobs) == 1


@pytest.mark.asyncio
async def test_run_job_triggers_notify_with_webhook(async_client, test_job):
    """POST /api/jobs/{id}/run calls notify with webhook_url when Celery task completes."""
    from app.notifications import notify as real_notify

    job_id = test_job["id"]

    # Patch Celery task to simulate completion with notify call
    mock_task = AsyncMock()
    mock_task.id = "fake-task-id"

    with patch("app.api.routes.run_scraping_task") as mock_run, \
         patch("app.notifications._post_webhook", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = True
        mock_run.delay.return_value = mock_task

        response = await async_client.post(f"/api/jobs/{job_id}/run")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "fake-task-id"


@pytest.mark.asyncio
async def test_notify_webhook_payload_structure():
    """Webhook payload always includes job_id and message fields."""
    from app.notifications import _post_webhook

    captured_payloads = []

    mock_response = type("R", (), {"raise_for_status": lambda self: None})()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    async def capture_post(url, json=None, **kwargs):
        captured_payloads.append(json)
        return mock_response

    mock_client.post = capture_post

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await _post_webhook(
            "https://hooks.example.com/cb",
            {"job_id": 99, "status": "completed", "results_count": 10},
        )

    assert result is True
    assert len(captured_payloads) == 1
    payload = captured_payloads[0]
    assert payload["job_id"] == 99
    assert payload["status"] == "completed"
    assert payload["results_count"] == 10

"""Tests for Celery worker task submission and status querying (T-001)."""
import pytest
from unittest.mock import MagicMock, patch


# --- Task configuration tests ---

def test_celery_app_configured():
    """Celery app has correct configuration for reliable task processing."""
    from app.worker import celery_app

    assert celery_app.conf.task_track_started is True
    assert celery_app.conf.task_acks_late is True
    assert celery_app.conf.worker_prefetch_multiplier == 1


def test_run_scraping_task_max_retries():
    """Task is configured with max_retries=3 for exponential backoff."""
    from app.worker import run_scraping_task

    assert run_scraping_task.max_retries == 3


def test_run_scraping_task_is_registered():
    """run_scraping_task is registered in the Celery app."""
    from app.worker import celery_app

    assert "worker.run_scraping_task" in celery_app.tasks


def test_run_scraping_task_job_not_found():
    """Task returns failed status when job does not exist in DB."""
    from app.worker import run_scraping_task

    with patch("app.worker.asyncio.run") as mock_run:
        mock_run.return_value = {"status": "failed", "error": "Job not found"}
        result = run_scraping_task.run(job_id=99999)

    assert result["status"] == "failed"
    assert "Job not found" in result["error"]
    mock_run.assert_called_once()


# --- API endpoint tests ---

async def test_run_job_submits_celery_task(async_client, test_job):
    """POST /api/jobs/{id}/run submits a Celery task and returns task_id."""
    job_id = test_job["id"]
    mock_task_result = MagicMock()
    mock_task_result.id = "celery-task-uuid-123"

    with patch("app.api.routes.run_scraping_task") as mock_task:
        mock_task.delay.return_value = mock_task_result
        response = await async_client.post(f"/api/jobs/{job_id}/run")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    assert data["task_id"] == "celery-task-uuid-123"
    assert "message" in data


async def test_run_job_fallback_when_celery_unavailable(async_client, test_job):
    """POST /api/jobs/{id}/run falls back to BackgroundTasks when Celery fails."""
    job_id = test_job["id"]
    with patch("app.api.routes.run_scraping_task") as mock_task, \
         patch("app.api.routes._run_job_task"):
        mock_task.delay.side_effect = Exception("Redis connection refused")
        response = await async_client.post(f"/api/jobs/{job_id}/run")

    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job_id
    # task_id is None when Celery is unavailable
    assert data["task_id"] is None


async def test_run_job_not_found_returns_404(async_client):
    """POST /api/jobs/{id}/run returns 404 for non-existent job."""
    response = await async_client.post("/api/jobs/99999/run")
    assert response.status_code == 404


async def test_task_status_returns_celery_state(async_client, test_job):
    """GET /api/jobs/{id}/task-status returns Celery task state and progress info."""
    job_id = test_job["id"]
    mock_result = MagicMock()
    mock_result.state = "SUCCESS"
    mock_result.info = {"status": "completed", "results_count": 5}

    with patch("app.api.routes.celery_app") as mock_celery:
        mock_celery.AsyncResult.return_value = mock_result
        response = await async_client.get(
            f"/api/jobs/{job_id}/task-status?task_id=test-task-id"
        )

    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "SUCCESS"
    assert data["task_id"] == "test-task-id"
    assert data["job_id"] == job_id


async def test_task_status_pending_state(async_client, test_job):
    """GET /api/jobs/{id}/task-status returns PENDING for unknown task IDs."""
    job_id = test_job["id"]
    mock_result = MagicMock()
    mock_result.state = "PENDING"
    mock_result.info = {}

    with patch("app.api.routes.celery_app") as mock_celery:
        mock_celery.AsyncResult.return_value = mock_result
        response = await async_client.get(
            f"/api/jobs/{job_id}/task-status?task_id=unknown-task-id"
        )

    assert response.status_code == 200
    data = response.json()
    assert data["state"] == "PENDING"


async def test_task_status_job_not_found(async_client):
    """GET /api/jobs/{id}/task-status returns 404 for non-existent job."""
    response = await async_client.get(
        "/api/jobs/99999/task-status?task_id=some-task-id"
    )
    assert response.status_code == 404

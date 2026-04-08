"""Tests for notifications.py - notify() and webhook delivery."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call


@pytest.mark.asyncio
async def test_notify_publishes_to_redis():
    """notify() publishes the message to the correct Redis Pub/Sub channel."""
    from app.notifications import notify

    mock_redis = AsyncMock()
    job_id = 42
    message = {"status": "completed", "results_count": 5}

    await notify(job_id, message, redis=mock_redis)

    mock_redis.publish.assert_called_once()
    channel_arg, payload_arg = mock_redis.publish.call_args[0]
    assert channel_arg == f"scraper:progress:{job_id}"
    parsed = json.loads(payload_arg)
    assert parsed["status"] == "completed"
    assert parsed["results_count"] == 5


@pytest.mark.asyncio
async def test_notify_no_redis_does_not_raise():
    """notify() with redis=None completes without error."""
    from app.notifications import notify

    # Should not raise
    await notify(1, {"status": "completed"}, redis=None)


@pytest.mark.asyncio
async def test_notify_redis_failure_is_silent():
    """notify() swallows Redis publish errors gracefully."""
    from app.notifications import notify

    mock_redis = AsyncMock()
    mock_redis.publish.side_effect = ConnectionError("Redis down")

    # Should not raise
    await notify(1, {"status": "running"}, redis=mock_redis)


@pytest.mark.asyncio
async def test_notify_calls_webhook_when_url_provided():
    """notify() calls _post_webhook when webhook_url is set."""
    from app.notifications import notify

    with patch("app.notifications._post_webhook", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = True
        await notify(7, {"status": "completed"}, webhook_url="https://example.com/hook")

    mock_post.assert_called_once()
    call_args = mock_post.call_args[0]
    assert call_args[0] == "https://example.com/hook"
    payload = call_args[1]
    assert payload["job_id"] == 7
    assert payload["status"] == "completed"


@pytest.mark.asyncio
async def test_notify_no_webhook_when_url_is_none():
    """notify() does not call _post_webhook when webhook_url is None."""
    from app.notifications import notify

    with patch("app.notifications._post_webhook", new_callable=AsyncMock) as mock_post:
        await notify(3, {"status": "completed"}, webhook_url=None)

    mock_post.assert_not_called()


@pytest.mark.asyncio
async def test_post_webhook_success():
    """_post_webhook returns True on a successful POST."""
    from app.notifications import _post_webhook

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await _post_webhook("https://example.com/hook", {"job_id": 1})

    assert result is True
    mock_client.post.assert_called_once_with("https://example.com/hook", json={"job_id": 1})


@pytest.mark.asyncio
async def test_post_webhook_retries_on_failure():
    """_post_webhook retries WEBHOOK_MAX_RETRIES times before giving up."""
    from app.notifications import _post_webhook, WEBHOOK_MAX_RETRIES

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(side_effect=ConnectionError("refused"))

    with patch("httpx.AsyncClient", return_value=mock_client), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        result = await _post_webhook("https://example.com/hook", {"job_id": 1})

    assert result is False
    assert mock_client.post.call_count == WEBHOOK_MAX_RETRIES


@pytest.mark.asyncio
async def test_post_webhook_succeeds_on_second_attempt():
    """_post_webhook returns True when a retry succeeds."""
    from app.notifications import _post_webhook

    mock_response = MagicMock()
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    # Fail first, succeed second
    mock_client.post = AsyncMock(
        side_effect=[ConnectionError("refused"), mock_response]
    )

    with patch("httpx.AsyncClient", return_value=mock_client), \
         patch("asyncio.sleep", new_callable=AsyncMock):
        result = await _post_webhook("https://example.com/hook", {"job_id": 1})

    assert result is True
    assert mock_client.post.call_count == 2

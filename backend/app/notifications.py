"""Webhook and Redis Pub/Sub notification support."""
import asyncio
import json
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

WEBHOOK_MAX_RETRIES = 3
WEBHOOK_CHANNEL_PREFIX = "scraper:progress"


async def _post_webhook(url: str, payload: dict) -> bool:
    """POST payload to webhook URL with up to WEBHOOK_MAX_RETRIES attempts."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(WEBHOOK_MAX_RETRIES):
            try:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                logger.info(f"Webhook POST to {url} succeeded on attempt {attempt + 1}")
                return True
            except Exception as exc:
                if attempt < WEBHOOK_MAX_RETRIES - 1:
                    wait = 2 ** attempt  # 1s, 2s
                    logger.warning(
                        f"Webhook POST to {url} failed (attempt {attempt + 1}): {exc}. "
                        f"Retrying in {wait}s..."
                    )
                    await asyncio.sleep(wait)
                else:
                    logger.error(
                        f"Webhook POST to {url} failed after {WEBHOOK_MAX_RETRIES} attempts: {exc}"
                    )
    return False


async def notify(
    job_id: int,
    message: dict,
    webhook_url: Optional[str] = None,
    redis=None,
) -> None:
    """Publish progress to Redis Pub/Sub and optionally POST to webhook.

    Args:
        job_id: The job identifier.
        message: The message payload to publish.
        webhook_url: Optional URL to POST results to on completion.
        redis: Optional async Redis client for Pub/Sub publishing.
    """
    # Publish to Redis Pub/Sub
    if redis is not None:
        try:
            channel = f"{WEBHOOK_CHANNEL_PREFIX}:{job_id}"
            await redis.publish(channel, json.dumps(message))
        except Exception as exc:
            logger.warning(f"Redis publish failed for job {job_id}: {exc}")

    # POST to webhook
    if webhook_url:
        payload = {"job_id": job_id, **message}
        await _post_webhook(webhook_url, payload)

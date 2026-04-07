import asyncio
import logging
import os
from datetime import datetime, timezone

from celery import Celery
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "smart_scraper",
    broker=REDIS_URL,
    backend=REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(
    bind=True,
    name="worker.run_scraping_task",
    max_retries=3,
    default_retry_delay=60,
)
def run_scraping_task(self, job_id: int):
    """Celery task to run a scraping job with retry and exponential backoff."""

    async def _run():
        from sqlalchemy import select, func
        from app.db.database import async_session_factory
        from app.db.models import Job, Result
        from app.scraper.engine import ScrapingEngine

        async with async_session_factory() as db:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()
            if not job:
                logger.error(f"Job {job_id} not found")
                return {"status": "failed", "error": "Job not found"}

            job.status = "running"
            job.updated_at = datetime.now(timezone.utc)
            await db.commit()

            try:
                self.update_state(
                    state="STARTED",
                    meta={"job_id": job_id, "progress": 0},
                )
                engine = ScrapingEngine(job_id=job_id, db_session=db)
                summary = await engine.run(job)

                job.status = summary.get("status", "completed")
                job.last_run = datetime.now(timezone.utc)
                job.updated_at = datetime.now(timezone.utc)

                count_result = await db.execute(
                    select(func.count(Result.id)).where(Result.job_id == job_id)
                )
                job.results_count = count_result.scalar() or 0
                await db.commit()

                return {"status": job.status, "results_count": job.results_count}

            except Exception as exc:
                job.status = "failed"
                job.updated_at = datetime.now(timezone.utc)
                await db.commit()
                raise exc

    try:
        return asyncio.run(_run())
    except Exception as exc:
        logger.error(f"Task failed for job {job_id}: {exc}")
        # Exponential backoff: 60s, 120s, 240s
        retry_countdown = 2 ** self.request.retries * 60
        raise self.retry(exc=exc, countdown=retry_countdown)

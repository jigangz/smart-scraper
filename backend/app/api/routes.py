import asyncio
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, select, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.models import Job, Result, Log
from app.api.schemas import (
    AutoDiscoverRequest,
    JobCreate,
    JobResponse,
    JobListResponse,
    ResultResponse,
    StatsResponse,
    LogResponse,
)
from app.scraper.engine import ScrapingEngine
from app.export.exporter import export_csv, export_json
from app.worker import run_scraping_task, celery_app

logger = logging.getLogger(__name__)

router = APIRouter()


async def _notify_ws(job_id: int, message: dict):
    """Publish a message to the Redis Pub/Sub channel for a job."""
    from app.notifications import notify
    try:
        import redis.asyncio as aioredis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = aioredis.from_url(redis_url)
        await notify(job_id, message, redis=r)
        await r.aclose()
    except Exception as exc:
        logger.warning(f"Redis notification failed for job {job_id}: {exc}")


async def _run_job_task(job_id: int):
    """Background task to run a scraping job."""
    from app.db.database import async_session_factory

    async with async_session_factory() as db:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if not job:
            return

        # Update status to running
        job.status = "running"
        job.updated_at = datetime.now(timezone.utc)
        await db.commit()

        await _notify_ws(job_id, {"status": "running", "message": "Job started"})

        engine = ScrapingEngine(job_id=job_id, db_session=db)
        summary = await engine.run(job)

        # Update job with results
        job.status = summary.get("status", "completed")
        job.last_run = datetime.now(timezone.utc)
        job.updated_at = datetime.now(timezone.utc)

        # Count total results for this job
        count_result = await db.execute(
            select(func.count(Result.id)).where(Result.job_id == job_id)
        )
        job.results_count = count_result.scalar() or 0

        await db.commit()

        await _notify_ws(job_id, {
            "status": job.status,
            "message": f"Job finished: {summary.get('results_count', 0)} results",
            "results_count": summary.get("results_count", 0),
        })


# --- Job CRUD ---

@router.post("/api/jobs", response_model=JobResponse, status_code=201)
async def create_job(job_data: JobCreate, db: AsyncSession = Depends(get_db)):
    interactions_data = None
    if job_data.interactions:
        interactions_data = [step.model_dump() for step in job_data.interactions]

    cookies_data = None
    if job_data.cookies:
        from app.cookie_encryption import encrypt_cookies
        raw = [c.model_dump() for c in job_data.cookies]
        cookies_data = encrypt_cookies(raw)

    job = Job(
        name=job_data.name,
        url=job_data.url,
        selectors=job_data.selectors,
        pagination_config=job_data.pagination_config,
        schedule=job_data.schedule,
        anti_detection=job_data.anti_detection,
        mode=job_data.mode,
        webhook_url=job_data.webhook_url,
        interactions=interactions_data,
        cookies=cookies_data,
        status="idle",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # If schedule is set, add to scheduler
    if job.schedule:
        try:
            from app.main import scheduler
            scheduler.add_job(job.id, job.schedule, _run_scheduled_job)
        except Exception as e:
            logger.warning(f"Could not schedule job {job.id}: {e}")

    return job


@router.get("/api/jobs", response_model=JobListResponse)
async def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    # Get total count
    count_result = await db.execute(select(func.count(Job.id)))
    total = count_result.scalar() or 0

    # Get jobs
    result = await db.execute(
        select(Job).order_by(Job.created_at.desc()).offset(skip).limit(limit)
    )
    jobs = result.scalars().all()

    return JobListResponse(jobs=jobs, total=total)


@router.get("/api/jobs/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/api/jobs/{job_id}/run")
async def run_job(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status == "running":
        raise HTTPException(status_code=409, detail="Job is already running")

    task_id = None
    try:
        task = run_scraping_task.delay(job_id)
        task_id = task.id
    except Exception as e:
        logger.warning(f"Celery unavailable, falling back to BackgroundTasks: {e}")
        background_tasks.add_task(_run_job_task, job_id)

    return {"message": "Job execution started", "job_id": job_id, "task_id": task_id}


@router.get("/api/jobs/{job_id}/task-status")
async def get_task_status(
    job_id: int,
    task_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Job).where(Job.id == job_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Job not found")

    async_result = celery_app.AsyncResult(task_id)
    state = async_result.state
    info = async_result.info if isinstance(async_result.info, dict) else {}

    return {"job_id": job_id, "task_id": task_id, "state": state, "info": info}


@router.delete("/api/jobs/{job_id}")
async def delete_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Remove from scheduler if scheduled
    try:
        from app.main import scheduler
        scheduler.remove_job(job_id)
    except Exception:
        pass

    await db.delete(job)
    await db.commit()

    return {"message": "Job deleted", "job_id": job_id}


# --- Results ---

@router.get("/api/results/{job_id}", response_model=list[ResultResponse])
async def get_results(
    job_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    # Verify job exists
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    if not job_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Job not found")

    result = await db.execute(
        select(Result)
        .where(Result.job_id == job_id)
        .order_by(Result.scraped_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/api/results/{job_id}/export")
async def export_results(
    job_id: int,
    format: str = Query("json", regex="^(csv|json)$"),
    db: AsyncSession = Depends(get_db),
):
    # Verify job exists
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Fetch all results
    result = await db.execute(
        select(Result)
        .where(Result.job_id == job_id)
        .order_by(Result.scraped_at.desc())
    )
    results = result.scalars().all()

    if not results:
        raise HTTPException(status_code=404, detail="No results to export")

    # Extract data from result objects
    data = [r.data for r in results if r.data]

    filename = f"job_{job_id}_{job.name.replace(' ', '_')}"

    if format == "csv":
        filepath = export_csv(data, filename)
        media_type = "text/csv"
    else:
        filepath = export_json(data, filename)
        media_type = "application/json"

    return FileResponse(
        filepath,
        media_type=media_type,
        filename=os.path.basename(filepath),
    )


# --- Stats ---

@router.get("/api/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    # Total jobs
    total_jobs_result = await db.execute(select(func.count(Job.id)))
    total_jobs = total_jobs_result.scalar() or 0

    # Active jobs (running or scheduled)
    active_jobs_result = await db.execute(
        select(func.count(Job.id)).where(
            Job.status.in_(["running", "scheduled"])
        )
    )
    active_jobs = active_jobs_result.scalar() or 0

    # Total results
    total_results_result = await db.execute(select(func.count(Result.id)))
    total_results = total_results_result.scalar() or 0

    # Success rate
    completed_result = await db.execute(
        select(func.count(Job.id)).where(Job.status == "completed")
    )
    completed = completed_result.scalar() or 0

    failed_result = await db.execute(
        select(func.count(Job.id)).where(Job.status == "failed")
    )
    failed = failed_result.scalar() or 0

    total_finished = completed + failed
    success_rate = (completed / total_finished * 100) if total_finished > 0 else 100.0

    # Recent activity (last 7 days)
    recent_activity = []
    for i in range(6, -1, -1):
        day = datetime.now(timezone.utc) - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)

        count_result = await db.execute(
            select(func.count(Result.id)).where(
                Result.scraped_at >= day_start,
                Result.scraped_at < day_end,
            )
        )
        count = count_result.scalar() or 0
        recent_activity.append({
            "date": day_start.strftime("%Y-%m-%d"),
            "count": count,
        })

    return StatsResponse(
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        total_results=total_results,
        success_rate=round(success_rate, 1),
        recent_activity=recent_activity,
    )


# --- Logs ---

@router.get("/api/logs/{job_id}", response_model=list[LogResponse])
async def get_logs(
    job_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Log)
        .where(Log.job_id == job_id)
        .order_by(Log.timestamp.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


# --- WebSocket ---

@router.websocket("/ws/jobs/{job_id}")
async def websocket_job_progress(websocket: WebSocket, job_id: int):
    await websocket.accept()

    # Send initial status
    from app.db.database import async_session_factory
    async with async_session_factory() as db:
        result = await db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if job:
            await websocket.send_json({
                "status": job.status,
                "message": f"Connected. Current status: {job.status}",
                "results_count": job.results_count,
            })

    # Try to subscribe to Redis Pub/Sub for real-time updates
    redis_client = None
    redis_listen_task = None
    try:
        import redis.asyncio as aioredis
        import json as _json
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = aioredis.from_url(redis_url)
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(f"scraper:progress:{job_id}")

        async def _listen_redis():
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    try:
                        data = _json.loads(msg["data"])
                        await websocket.send_json(data)
                    except Exception:
                        pass

        redis_listen_task = asyncio.create_task(_listen_redis())
    except Exception as exc:
        logger.warning(f"Redis Pub/Sub unavailable for job {job_id}: {exc}")

    try:
        while True:
            try:
                data = await websocket.receive_text()
                if data == "ping":
                    await websocket.send_json({"type": "pong"})
            except WebSocketDisconnect:
                break
    finally:
        if redis_listen_task:
            redis_listen_task.cancel()
        if redis_client:
            try:
                await redis_client.aclose()
            except Exception:
                pass


# --- LLM auto-selector discovery ---

@router.post("/api/jobs/auto-discover")
async def auto_discover(request: AutoDiscoverRequest):
    """Fetch page HTML, send to Groq LLM, return suggested CSS selectors + samples."""
    from app.auto_discover import auto_discover_selectors

    redis_client = None
    try:
        import redis.asyncio as aioredis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        redis_client = aioredis.from_url(redis_url)
    except Exception:
        pass

    try:
        result = await auto_discover_selectors(request.url, redis=redis_client)
    finally:
        if redis_client is not None:
            try:
                await redis_client.aclose()
            except Exception:
                pass

    return result


# --- Helper for scheduled jobs ---

async def _run_scheduled_job(job_id: int):
    """Called by the scheduler to run a job."""
    await _run_job_task(job_id)


# --- Observability helpers (patchable in tests) ---

async def _check_redis() -> str:
    """Ping Redis and return 'healthy' or 'unavailable'."""
    try:
        import redis.asyncio as aioredis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        r = aioredis.from_url(redis_url)
        await r.ping()
        await r.aclose()
        return "healthy"
    except Exception:
        return "unavailable"


async def _check_celery() -> str:
    """Inspect Celery workers and return 'healthy' or 'unavailable'."""
    try:
        import asyncio as _asyncio

        def _do_inspect():
            i = celery_app.control.inspect(timeout=1.0)
            return i.ping()

        loop = _asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _do_inspect)
        return "healthy" if result else "unavailable"
    except Exception:
        return "unavailable"


async def _check_db() -> str:
    """Run a trivial DB query and return 'healthy' or 'unhealthy'."""
    try:
        from app.db.database import async_session_factory
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return "healthy"
    except Exception:
        return "unhealthy"


# --- Observability endpoints ---

@router.get("/metrics")
async def prometheus_metrics():
    """Return Prometheus-format metrics."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    import app.metrics  # ensure metrics are registered  # noqa: F401
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@router.get("/health")
async def health_check():
    """Return service health status with sub-component checks."""
    redis_status = await _check_redis()
    celery_status = await _check_celery()
    db_status = await _check_db()

    checks = {
        "redis": redis_status,
        "celery": celery_status,
        "db": db_status,
    }

    if db_status != "healthy":
        status = "unhealthy"
    elif redis_status != "healthy" or celery_status != "healthy":
        status = "degraded"
    else:
        status = "healthy"

    return {"status": status, "checks": checks}

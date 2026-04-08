import logging
import os
import re
from typing import Callable, Optional

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


def parse_schedule(schedule: str) -> dict:
    """
    Parse a schedule string into a dict with type and parameters.

    Supports:
    - Interval strings: "30m", "2h", "1d"
    - Cron expressions: "0 */6 * * *" (minute hour dom month dow)

    Returns dict with 'type' key ('interval' or 'cron') and config values.
    """
    schedule = schedule.strip()

    # Interval format: 30m, 2h, 1d
    match = re.fullmatch(r"(\d+)(m|h|d)", schedule)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        multipliers = {"m": 60, "h": 3600, "d": 86400}
        return {"type": "interval", "every": value * multipliers[unit]}

    # Cron format: "minute hour dom month dow"
    parts = schedule.split()
    if len(parts) == 5:
        return {
            "type": "cron",
            "minute": parts[0],
            "hour": parts[1],
            "day_of_month": parts[2],
            "month_of_year": parts[3],
            "day_of_week": parts[4],
        }

    raise ValueError(
        f"Invalid schedule format: '{schedule}'. "
        f"Use cron (e.g., '0 */6 * * *') or interval (e.g., '30m', '2h', '1d')."
    )


class JobScheduler:
    """
    Celery Beat scheduler backed by Redis via redbeat.
    Schedules persist across restarts because entries are stored in Redis.
    """

    def start(self):
        logger.info("Celery Beat scheduler active — schedules stored in Redis")

    def stop(self):
        logger.info("Celery Beat scheduler shutdown")

    def add_job(self, job_id: int, schedule: str, func: Optional[Callable] = None):
        """Register a periodic job with Celery Beat via redbeat."""
        from redbeat import RedBeatSchedulerEntry
        from celery.schedules import crontab
        from celery.schedules import schedule as celery_schedule
        from app.worker import celery_app

        parsed = parse_schedule(schedule)
        entry_name = f"job_{job_id}"

        if parsed["type"] == "interval":
            celery_sched = celery_schedule(parsed["every"])
        else:
            celery_sched = crontab(
                minute=parsed["minute"],
                hour=parsed["hour"],
                day_of_week=parsed["day_of_week"],
                day_of_month=parsed["day_of_month"],
                month_of_year=parsed["month_of_year"],
            )

        entry = RedBeatSchedulerEntry(
            entry_name,
            "worker.run_scraping_task",
            celery_sched,
            args=[job_id],
            app=celery_app,
        )
        entry.save()
        logger.info(f"Scheduled job {job_id} with schedule: {schedule}")

    def remove_job(self, job_id: int):
        """Remove a periodic job from Celery Beat schedule."""
        try:
            from redbeat import RedBeatSchedulerEntry
            from app.worker import celery_app

            entry_name = f"job_{job_id}"
            entry = RedBeatSchedulerEntry.from_key(
                f"redbeat:{entry_name}", app=celery_app
            )
            entry.delete()
            logger.info(f"Removed scheduled job {job_id}")
        except Exception:
            pass  # Job may not exist

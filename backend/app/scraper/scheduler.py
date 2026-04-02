import logging
from typing import Callable
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class JobScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()

    def start(self):
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    def stop(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("Scheduler stopped")

    def add_job(self, job_id: int, schedule: str, func: Callable):
        """
        Add a scheduled job. Schedule can be:
        - A cron expression (e.g., "0 */6 * * *")
        - An interval string (e.g., "30m", "2h", "1d")
        """
        str_job_id = f"job_{job_id}"

        # Remove existing job if present
        self.remove_job(job_id)

        try:
            trigger = self._parse_schedule(schedule)
            self.scheduler.add_job(
                func,
                trigger=trigger,
                id=str_job_id,
                replace_existing=True,
                kwargs={"job_id": job_id},
            )
            logger.info(f"Scheduled job {job_id} with schedule: {schedule}")
        except Exception as e:
            logger.error(f"Failed to schedule job {job_id}: {e}")
            raise

    def remove_job(self, job_id: int):
        str_job_id = f"job_{job_id}"
        try:
            self.scheduler.remove_job(str_job_id)
            logger.info(f"Removed scheduled job {job_id}")
        except Exception:
            pass  # Job may not exist

    def _parse_schedule(self, schedule: str):
        """Parse schedule string into an APScheduler trigger."""
        schedule = schedule.strip()

        # Try interval format first (e.g., "30m", "2h", "1d")
        if schedule.endswith("m"):
            try:
                minutes = int(schedule[:-1])
                return IntervalTrigger(minutes=minutes)
            except ValueError:
                pass
        elif schedule.endswith("h"):
            try:
                hours = int(schedule[:-1])
                return IntervalTrigger(hours=hours)
            except ValueError:
                pass
        elif schedule.endswith("d"):
            try:
                days = int(schedule[:-1])
                return IntervalTrigger(days=days)
            except ValueError:
                pass

        # Try cron expression
        parts = schedule.split()
        if len(parts) == 5:
            return CronTrigger.from_crontab(schedule)

        raise ValueError(
            f"Invalid schedule format: '{schedule}'. "
            f"Use cron (e.g., '0 */6 * * *') or interval (e.g., '30m', '2h', '1d')."
        )

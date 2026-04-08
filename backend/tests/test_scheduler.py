"""Tests for Celery Beat scheduler (T-003)."""
import pytest
from unittest.mock import MagicMock, patch

from app.scraper.scheduler import parse_schedule, JobScheduler


# --- parse_schedule tests ---

class TestParseSchedule:
    def test_interval_minutes(self):
        result = parse_schedule("30m")
        assert result == {"type": "interval", "every": 1800}

    def test_interval_hours(self):
        result = parse_schedule("2h")
        assert result == {"type": "interval", "every": 7200}

    def test_interval_days(self):
        result = parse_schedule("1d")
        assert result == {"type": "interval", "every": 86400}

    def test_cron_expression(self):
        result = parse_schedule("0 */6 * * *")
        assert result["type"] == "cron"
        assert result["minute"] == "0"
        assert result["hour"] == "*/6"
        assert result["day_of_month"] == "*"
        assert result["month_of_year"] == "*"
        assert result["day_of_week"] == "*"

    def test_cron_complex(self):
        result = parse_schedule("0 9 * * 1-5")
        assert result["type"] == "cron"
        assert result["minute"] == "0"
        assert result["hour"] == "9"
        assert result["day_of_week"] == "1-5"

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Invalid schedule format"):
            parse_schedule("invalid")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            parse_schedule("")

    def test_whitespace_stripped(self):
        result = parse_schedule("  30m  ")
        assert result == {"type": "interval", "every": 1800}


# --- JobScheduler tests ---

class TestJobScheduler:
    def test_start_does_not_raise(self):
        scheduler = JobScheduler()
        scheduler.start()  # Should not raise

    def test_stop_does_not_raise(self):
        scheduler = JobScheduler()
        scheduler.stop()  # Should not raise

    def test_add_job_interval_calls_save(self):
        """add_job with interval schedule creates and saves a redbeat entry."""
        scheduler = JobScheduler()
        mock_entry = MagicMock()
        mock_entry_class = MagicMock(return_value=mock_entry)
        mock_redbeat = MagicMock()
        mock_redbeat.RedBeatSchedulerEntry = mock_entry_class

        with patch.dict("sys.modules", {"redbeat": mock_redbeat}), \
             patch("app.scraper.scheduler.celery_schedule", create=True), \
             patch("app.worker.celery_app", MagicMock()):
            scheduler.add_job(1, "30m")

        mock_entry.save.assert_called_once()

    def test_add_job_cron_calls_save(self):
        """add_job with cron schedule creates and saves a redbeat entry."""
        scheduler = JobScheduler()
        mock_entry = MagicMock()
        mock_entry_class = MagicMock(return_value=mock_entry)
        mock_redbeat = MagicMock()
        mock_redbeat.RedBeatSchedulerEntry = mock_entry_class

        with patch.dict("sys.modules", {"redbeat": mock_redbeat}), \
             patch("app.worker.celery_app", MagicMock()):
            scheduler.add_job(2, "0 */6 * * *")

        mock_entry.save.assert_called_once()

    def test_remove_job_no_error_when_missing(self):
        """remove_job silently succeeds when job does not exist."""
        scheduler = JobScheduler()
        mock_redbeat = MagicMock()
        mock_redbeat.RedBeatSchedulerEntry.from_key.side_effect = Exception("not found")

        with patch.dict("sys.modules", {"redbeat": mock_redbeat}), \
             patch("app.worker.celery_app", MagicMock()):
            scheduler.remove_job(999)  # Should not raise

    def test_remove_job_calls_delete(self):
        """remove_job calls delete() on the redbeat entry."""
        scheduler = JobScheduler()
        mock_entry = MagicMock()
        mock_redbeat = MagicMock()
        mock_redbeat.RedBeatSchedulerEntry.from_key.return_value = mock_entry

        with patch.dict("sys.modules", {"redbeat": mock_redbeat}), \
             patch("app.worker.celery_app", MagicMock()):
            scheduler.remove_job(1)

        mock_entry.delete.assert_called_once()

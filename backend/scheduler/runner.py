"""Hourly background scheduler.

Runs `run_automation` on a repeating interval (default 60 minutes) in a
background daemon thread. Used by the FastAPI lifespan and the CLI so the
automation is always active while the app is up.
"""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone

from config import get_settings
from scheduler.jobs import run_automation
from utils.logger import get_logger

logger = get_logger("scheduler.runner")


class Scheduler:
    def __init__(self, interval_minutes: int | None = None) -> None:
        settings = get_settings()
        self.interval_seconds = (interval_minutes or settings.schedule_interval_minutes) * 60
        self.run_on_startup = settings.run_on_startup
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return

        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="jobhunter-scheduler", daemon=True)
        self._thread.start()
        logger.info(
            "Scheduler started (every %ss, run-on-startup=%s)",
            self.interval_seconds,
            self.run_on_startup,
        )

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None
        logger.info("Scheduler stopped.")

    def _run(self) -> None:
        # Optionally run once on startup, then wait for the next interval.
        if self.run_on_startup:
            self._run_once()

        while not self._stop.is_set():
            if self._stop.wait(self.interval_seconds):
                break
            self._run_once()

    def _run_once(self) -> None:
        logger.info("Scheduled scrape starting at %s", datetime.now(timezone.utc).isoformat())
        try:
            report = run_automation(triggered_by="scheduler")
            logger.info(
                "Scheduled scrape done: fetched=%s new=%s matched=%s in %.2fs",
                report.total_fetched,
                report.new_jobs,
                report.notified.get("matched", 0),
                report.duration_seconds,
            )
        except Exception as exc:
            logger.exception("Scheduled scrape failed: %s", exc)

    def run_forever(self) -> None:
        """Block the calling thread until stop() is called (for CLI use)."""
        self.start()
        try:
            while self._thread and self._thread.is_alive():
                time.sleep(1)
        finally:
            self.stop()

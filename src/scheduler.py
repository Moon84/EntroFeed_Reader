# -*- coding: utf-8 -*-
"""Scheduler module for EntroFeed.

This module provides a centralized task scheduling system using APScheduler.
It replaces the ad-hoc repeat_every decorator with a robust, persistent scheduler.

Usage:
    from src.scheduler import get_scheduler

    scheduler = get_scheduler()
    scheduler.add_poll_feeds_task(interval_minutes=5)
    scheduler.start()
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR

logger = logging.getLogger("scheduler")


class SchedulerManager:
    """Singleton scheduler manager using APScheduler.

    Provides centralized task scheduling with support for:
    - Interval-based triggers (RSS polling)
    - Cron-based triggers (daily digest, interest inference)
    - Persistent job stores
    - Error handling and logging
    """

    _instance: Optional["SchedulerManager"] = None
    _initialized: bool = False

    def __init__(self):
        """Initialize the scheduler manager."""
        if SchedulerManager._initialized:
            return

        self.scheduler = AsyncIOScheduler(
            jobstores={
                "default": MemoryJobStore(),
            },
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 60 * 5,  # 5 minutes grace period
            },
            timezone=timezone.utc,
        )

        # Register event listeners
        self.scheduler.add_listener(
            self._job_executed_listener,
            EVENT_JOB_EXECUTED | EVENT_JOB_ERROR,
        )

        SchedulerManager._initialized = True
        logger.info("SchedulerManager initialized")

    @classmethod
    def get_instance(cls) -> "SchedulerManager":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = SchedulerManager()
        return cls._instance

    def _job_executed_listener(self, event):
        """Handle job execution events."""
        if event.exception:
            logger.error(f"Job {event.job_id} failed: {event.exception}")
        else:
            logger.debug(f"Job {event.job_id} executed successfully")

    def add_interval_task(
        self,
        task_id: str,
        func: Callable,
        minutes: int,
        **kwargs: Any,
    ) -> None:
        """Add an interval-based task.

        Args:
            task_id: Unique identifier for the task
            func: Async function to execute
            minutes: Interval in minutes
            **kwargs: Additional arguments to pass to the function
        """
        # Remove existing task with same ID if exists
        if self.scheduler.get_job(task_id):
            self.scheduler.remove_job(task_id)
            logger.info(f"Removed existing task: {task_id}")

        trigger = IntervalTrigger(minutes=minutes, timezone=timezone.utc)

        self.scheduler.add_job(
            func,
            trigger,
            id=task_id,
            name=task_id,
            replace_existing=True,
            **kwargs,
        )

        logger.info(f"Added interval task '{task_id}' with {minutes}min interval")

    def add_cron_task(
        self,
        task_id: str,
        func: Callable,
        hour: int = 0,
        minute: int = 0,
        **kwargs: Any,
    ) -> None:
        """Add a cron-based task (runs at specific time daily).

        Args:
            task_id: Unique identifier for the task
            func: Async function to execute
            hour: Hour to run (0-23)
            minute: Minute to run (0-59)
            **kwargs: Additional arguments to pass to the function
        """
        if self.scheduler.get_job(task_id):
            self.scheduler.remove_job(task_id)
            logger.info(f"Removed existing task: {task_id}")

        trigger = CronTrigger(hour=hour, minute=minute, timezone=timezone.utc)

        self.scheduler.add_job(
            func,
            trigger,
            id=task_id,
            name=task_id,
            replace_existing=True,
            **kwargs,
        )

        logger.info(f"Added cron task '{task_id}' at {hour:02d}:{minute:02d}")

    def remove_task(self, task_id: str) -> bool:
        """Remove a task by ID.

        Args:
            task_id: Task identifier

        Returns:
            True if task was removed, False if not found
        """
        job = self.scheduler.get_job(task_id)
        if job:
            self.scheduler.remove_job(task_id)
            logger.info(f"Removed task: {task_id}")
            return True
        return False

    def get_next_run_time(self, task_id: str) -> Optional[datetime]:
        """Get the next scheduled run time for a task.

        Args:
            task_id: Task identifier

        Returns:
            Next run datetime or None if not scheduled
        """
        job = self.scheduler.get_job(task_id)
        if job:
            return job.next_run_time
        return None

    def get_all_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Get all scheduled jobs.

        Returns:
            Dict of job info keyed by task ID
        """
        jobs = {}
        for job in self.scheduler.get_jobs():
            jobs[job.id] = {
                "name": job.name,
                "next_run_time": job.next_run_time,
                "trigger": str(job.trigger),
            }
        return jobs

    def start(self) -> None:
        """Start the scheduler."""
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("Scheduler started")

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown the scheduler.

        Args:
            wait: Whether to wait for running jobs to complete
        """
        if self.scheduler.running:
            self.scheduler.shutdown(wait=wait)
            logger.info("Scheduler shutdown")


# Singleton accessor
_scheduler: Optional[SchedulerManager] = None


def get_scheduler() -> SchedulerManager:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = SchedulerManager.get_instance()
    return _scheduler


# ============ Background Task Wrappers ============


async def poll_feeds_task() -> None:
    """Background task wrapper for RSS feed polling."""
    import asyncio
    from src.rss import EntroFeedRSS
    from src.storage.singleton import get_storage

    logger.info("Scheduled: Checking feeds for updates")

    try:
        storage_handler = get_storage()
        rss = EntroFeedRSS(db=storage_handler)

        # Run synchronous RSS polling in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, rss.check_feeds_sync)
    except Exception as e:
        logger.error(f"Scheduled feed polling failed: {e}")


async def infer_interests_task() -> None:
    """Background task wrapper for interest inference."""
    from src.ontology import get_ontology_registry

    logger.info("Scheduled: Inferring new interests")

    try:
        registry = get_ontology_registry()
        inferred = registry.infer_new_interests(max_new=5)
        if inferred:
            logger.info(f"Inferred {len(inferred)} new interests")
    except Exception as e:
        logger.error(f"Scheduled interest inference failed: {e}")


async def daily_digest_task() -> None:
    """Background task wrapper for daily digest generation."""
    from src.agents.tools import get_daily_digest
    import json

    logger.info("Scheduled: Generating daily digest")

    try:
        result = get_daily_digest()
        parsed = json.loads(result)
        logger.info(f"Daily digest generated: {parsed.get('count', 0)} entries")
    except Exception as e:
        logger.error(f"Scheduled daily digest failed: {e}")


# ============ Convenience Functions ============


def setup_rss_polling(interval_minutes: int = 5) -> None:
    """Setup RSS polling task.

    Args:
        interval_minutes: Polling interval in minutes
    """
    scheduler = get_scheduler()
    scheduler.add_interval_task(
        task_id="rss_polling",
        func=poll_feeds_task,
        minutes=interval_minutes,
    )


def setup_daily_tasks() -> None:
    """Setup daily scheduled tasks."""
    scheduler = get_scheduler()

    # Infer interests at 3 AM daily
    scheduler.add_cron_task(
        task_id="infer_interests",
        func=infer_interests_task,
        hour=3,
        minute=0,
    )

    # Generate daily digest at 8 AM daily
    scheduler.add_cron_task(
        task_id="daily_digest",
        func=daily_digest_task,
        hour=8,
        minute=0,
    )


def update_polling_interval(interval_minutes: int) -> None:
    """Update the RSS polling interval.

    Args:
        interval_minutes: New polling interval in minutes
    """
    scheduler = get_scheduler()
    scheduler.add_interval_task(
        task_id="rss_polling",
        func=poll_feeds_task,
        minutes=interval_minutes,
    )
    logger.info(f"Updated RSS polling interval to {interval_minutes} minutes")

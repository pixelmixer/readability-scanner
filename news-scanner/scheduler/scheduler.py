"""
RSS feed scanning scheduler with cron job functionality.
"""

import logging
import asyncio
from datetime import datetime
from typing import List
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import croniter

from database.sources import source_repository
from scanner.scanner import scan_single_source
from config import settings

logger = logging.getLogger(__name__)


class RSSScheduler:
    """RSS feed scanning scheduler using APScheduler."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.logger = logging.getLogger(__name__)

    def start(self):
        """Start the scheduler."""
        try:
            if self.is_running:
                self.logger.warning("Scheduler is already running")
                return

            # Validate cron expression
            if not self._validate_cron_expression(settings.scan_interval):
                self.logger.error(f"Invalid cron expression: {settings.scan_interval}")
                return

            # Add the scanning job
            self.scheduler.add_job(
                self._scan_all_sources,
                CronTrigger.from_crontab(settings.scan_interval),
                id='rss_scan_job',
                name='RSS Feed Scanning',
                replace_existing=True,
                max_instances=1  # Prevent overlapping executions
            )

            # Start the scheduler
            self.scheduler.start()
            self.is_running = True

            # Log schedule information
            human_readable = self._cron_to_human(settings.scan_interval)
            self.logger.info(f"✅ RSS Scheduler started")
            self.logger.info(f"📅 Schedule: {human_readable} ({settings.scan_interval})")

            # Run initial scan
            asyncio.create_task(self._initial_scan())

        except Exception as e:
            self.logger.error(f"Failed to start scheduler: {e}")
            raise

    def stop(self):
        """Stop the scheduler."""
        try:
            if not self.is_running:
                self.logger.warning("Scheduler is not running")
                return

            self.scheduler.shutdown(wait=True)
            self.is_running = False
            self.logger.info("🔄 RSS Scheduler stopped")

        except Exception as e:
            self.logger.error(f"Error stopping scheduler: {e}")

    def _validate_cron_expression(self, cron_expr: str) -> bool:
        """Validate cron expression syntax."""
        try:
            croniter.croniter(cron_expr)
            return True
        except (ValueError, TypeError):
            return False

    def _cron_to_human(self, cron_expr: str) -> str:
        """Convert cron expression to human-readable format."""
        try:
            from croniter import croniter
            from datetime import datetime, timedelta

            # Get next few run times to understand the pattern
            base = datetime.now()
            cron = croniter(cron_expr, base)

            next_runs = []
            for _ in range(3):
                next_runs.append(cron.get_next(datetime))

            # Simple interpretation based on common patterns
            if "0 */6 * * *" in cron_expr:
                return "Every 6 hours"
            elif "0 */4 * * *" in cron_expr:
                return "Every 4 hours"
            elif "0 */2 * * *" in cron_expr:
                return "Every 2 hours"
            elif "0 * * * *" in cron_expr:
                return "Every hour"
            elif "*/30 * * * *" in cron_expr:
                return "Every 30 minutes"
            elif "*/15 * * * *" in cron_expr:
                return "Every 15 minutes"
            elif "0 0 * * *" in cron_expr:
                return "Daily at midnight"
            else:
                # Calculate interval from first two runs
                if len(next_runs) >= 2:
                    interval = next_runs[1] - next_runs[0]
                    if interval.total_seconds() < 3600:
                        minutes = int(interval.total_seconds() / 60)
                        return f"Every {minutes} minutes"
                    elif interval.total_seconds() < 86400:
                        hours = int(interval.total_seconds() / 3600)
                        return f"Every {hours} hours"
                    else:
                        days = int(interval.total_seconds() / 86400)
                        return f"Every {days} days"

                return f"Custom schedule: {cron_expr}"

        except Exception:
            return cron_expr

    async def _initial_scan(self):
        """Perform initial scan on startup."""
        try:
            self.logger.info("🚀 Performing initial RSS scan on startup...")
            await self._scan_all_sources()
        except Exception as e:
            self.logger.error(f"Initial scan failed: {e}")

    async def _scan_all_sources(self):
        """Scan all configured RSS sources."""
        try:
            self.logger.info("⏰ Starting scheduled RSS scan")

            # Get all source URLs
            source_urls = await source_repository.get_source_urls()

            if not source_urls:
                self.logger.info("No RSS sources configured for scanning")
                return

            self.logger.info(f"📡 Scanning {len(source_urls)} RSS sources")

            # Scan all sources concurrently with limited parallelism
            scan_tasks = []
            for url in source_urls:
                task = self._scan_single_source_with_logging(url)
                scan_tasks.append(task)

            # Execute with controlled concurrency
            semaphore = asyncio.Semaphore(settings.max_concurrent_scans)

            async def limited_scan(task):
                async with semaphore:
                    return await task

            results = await asyncio.gather(
                *[limited_scan(task) for task in scan_tasks],
                return_exceptions=True
            )

            # Log summary results
            successful_scans = 0
            total_articles = 0
            failed_scans = 0

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    self.logger.error(f"Scan failed for {source_urls[i]}: {result}")
                    failed_scans += 1
                elif result:
                    successful_scans += 1
                    total_articles += result.stats.scanned

                    if result.has_high_failure_rate:
                        self.logger.warning(
                            f"⚠️ High failure rate for {result.source_name}: "
                            f"{result.stats.failure_rate:.1f}% ({result.stats.failed}/{result.stats.total})"
                        )

            self.logger.info(
                f"✅ Scheduled scan completed: {successful_scans}/{len(source_urls)} sources, "
                f"{total_articles} articles processed"
            )

            if failed_scans > 0:
                self.logger.warning(f"⚠️ {failed_scans} sources failed to scan")

        except Exception as e:
            self.logger.error(f"Error in scheduled scan: {e}")

    async def _scan_single_source_with_logging(self, source_url: str):
        """Scan a single source with enhanced logging."""
        try:
            # Get source name for logging
            source = await source_repository.get_source_by_url(source_url)
            source_name = source.name if source else source_url

            self.logger.debug(f"🔍 Scanning: {source_name}")

            # Perform scan
            result = await scan_single_source(source_url, source_name)

            if result.success:
                self.logger.info(
                    f"✅ {source_name}: {result.stats.scanned}/{result.stats.total} articles"
                )
            else:
                self.logger.error(f"❌ {source_name}: {result.error}")

            return result

        except Exception as e:
            self.logger.error(f"Error scanning {source_url}: {e}")
            raise

    def get_next_run_time(self) -> datetime:
        """Get the next scheduled run time."""
        try:
            if not self.is_running:
                return None

            job = self.scheduler.get_job('rss_scan_job')
            if job:
                return job.next_run_time

            return None

        except Exception:
            return None

    def get_status(self) -> dict:
        """Get scheduler status information."""
        next_run = self.get_next_run_time()

        return {
            "running": self.is_running,
            "schedule": settings.scan_interval,
            "schedule_human": self._cron_to_human(settings.scan_interval),
            "next_run": next_run.isoformat() if next_run else None,
            "next_run_human": next_run.strftime("%Y-%m-%d %H:%M:%S") if next_run else None
        }


# Global scheduler instance
rss_scheduler = RSSScheduler()


def start_scheduler():
    """Start the global RSS scheduler."""
    rss_scheduler.start()


def stop_scheduler():
    """Stop the global RSS scheduler."""
    rss_scheduler.stop()

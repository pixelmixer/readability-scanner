"""
Celery tasks for RSS scanning and article processing.
"""

import logging
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timedelta

from celery import Task
from celery.exceptions import Retry

# Import the Celery app
from celery_app.celery_worker import celery_app

# Import existing scanner functionality
from scanner.scanner import scan_single_source
from database.sources import source_repository
from database.articles import article_repository
from database.connection import db_manager

logger = logging.getLogger(__name__)


async def ensure_database_connection():
    """Ensure database connection is established for Celery tasks."""
    if not db_manager._connected:
        logger.info("🔗 Establishing database connection for Celery task")
        await db_manager.connect()
    else:
        # Verify connection is still healthy
        if not await db_manager.health_check():
            logger.warning("🔄 Database connection unhealthy, reconnecting...")
            await db_manager.disconnect()
            await db_manager.connect()


class CallbackTask(Task):
    """Base task class with enhanced error handling and logging."""

    def on_success(self, retval, task_id, args, kwargs):
        """Success callback."""
        logger.info(f"✅ Task {self.name} [{task_id}] completed successfully")

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Failure callback."""
        logger.error(f"❌ Task {self.name} [{task_id}] failed: {exc}")
        logger.error(f"🔍 Error info: {einfo}")

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Retry callback."""
        logger.warning(f"🔄 Task {self.name} [{task_id}] retry: {exc}")


@celery_app.task(bind=True, base=CallbackTask, name='celery_app.tasks.manual_refresh_source_task')
def manual_refresh_source_task(self, source_id: str, source_url: str) -> Dict[str, Any]:
    """
    High priority task for manual source refresh requests.
    These tasks get processed immediately for UI responsiveness.
    """
    try:
        logger.info(f"🔄 Manual refresh requested for source: {source_url}")

        # Run the async scanner in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Ensure database connection
            loop.run_until_complete(ensure_database_connection())

            # Get source name for better logging
            source = loop.run_until_complete(
                source_repository.get_source_by_id(source_id)
            )
            source_name = source.name if source else source_url

            # Perform the scan
            result = loop.run_until_complete(
                scan_single_source(source_url, source_name)
            )

            if result.success:
                logger.info(
                    f"✅ Manual refresh completed: {source_name} - "
                    f"{result.stats.scanned}/{result.stats.total} articles processed"
                )

                return {
                    'success': True,
                    'source_name': source_name,
                    'source_url': source_url,
                    'scanned': result.stats.scanned,
                    'total': result.stats.total,
                    'failed': result.stats.failed,
                    'failure_rate': result.stats.failure_rate,
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                logger.error(f"❌ Manual refresh failed: {source_name} - {result.error}")
                return {
                    'success': False,
                    'source_name': source_name,
                    'source_url': source_url,
                    'error': result.error,
                    'timestamp': datetime.utcnow().isoformat()
                }

        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"💥 Manual refresh task failed for {source_url}: {exc}")

        # Retry up to 2 times for manual requests
        if self.request.retries < 2:
            logger.info(f"🔄 Retrying manual refresh for {source_url} (attempt {self.request.retries + 1}/2)")
            raise self.retry(exc=exc, countdown=30, max_retries=2)

        return {
            'success': False,
            'source_url': source_url,
            'error': str(exc),
            'retries_exceeded': True,
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(bind=True, base=CallbackTask, name='celery_app.tasks.scan_single_source_task')
def scan_single_source_task(self, source_url: str, priority: int = 5) -> Dict[str, Any]:
    """
    Normal priority task for scanning individual RSS sources.
    Used for scheduled scans to distribute load over time.
    """
    try:
        logger.info(f"📡 Scanning RSS source: {source_url}")

        # Run the async scanner in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Ensure database connection
            loop.run_until_complete(ensure_database_connection())

            # Get source information
            source = loop.run_until_complete(
                source_repository.get_source_by_url(source_url)
            )
            source_name = source.name if source else source_url

            # Perform the scan
            result = loop.run_until_complete(
                scan_single_source(source_url, source_name)
            )

            if result.success:
                # Log results with appropriate level based on failure rate
                if result.has_high_failure_rate:
                    logger.warning(
                        f"⚠️ Source scan completed with high failures: {source_name} - "
                        f"{result.stats.scanned}/{result.stats.total} articles "
                        f"({result.stats.failure_rate:.1f}% failure rate)"
                    )
                else:
                    logger.info(
                        f"✅ Source scan completed: {source_name} - "
                        f"{result.stats.scanned}/{result.stats.total} articles processed"
                    )

                return {
                    'success': True,
                    'source_name': source_name,
                    'source_url': source_url,
                    'scanned': result.stats.scanned,
                    'total': result.stats.total,
                    'failed': result.stats.failed,
                    'failure_rate': result.stats.failure_rate,
                    'high_failure_rate': result.has_high_failure_rate,
                    'timestamp': datetime.utcnow().isoformat()
                }
            else:
                logger.error(f"❌ Source scan failed: {source_name} - {result.error}")
                return {
                    'success': False,
                    'source_name': source_name,
                    'source_url': source_url,
                    'error': result.error,
                    'timestamp': datetime.utcnow().isoformat()
                }

        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"💥 Source scan task failed for {source_url}: {exc}")

        # Retry up to 3 times for scheduled scans
        if self.request.retries < 3:
            # Exponential backoff: 2min, 4min, 8min
            countdown = 120 * (2 ** self.request.retries)
            logger.info(
                f"🔄 Retrying source scan for {source_url} in {countdown}s "
                f"(attempt {self.request.retries + 1}/3)"
            )
            raise self.retry(exc=exc, countdown=countdown, max_retries=3)

        return {
            'success': False,
            'source_url': source_url,
            'error': str(exc),
            'retries_exceeded': True,
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(bind=True, base=CallbackTask, name='celery_app.tasks.scheduled_scan_trigger_task')
def scheduled_scan_trigger_task(self) -> Dict[str, Any]:
    """
    Low priority task that triggers scheduled scans for all sources.
    Instead of running all scans simultaneously, this distributes them across time.
    """
    try:
        logger.info("⏰ Triggering scheduled RSS source scans")

        # Get all source URLs
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Ensure database connection
            loop.run_until_complete(ensure_database_connection())

            source_urls = loop.run_until_complete(source_repository.get_source_urls())
        finally:
            loop.close()

        if not source_urls:
            logger.info("No RSS sources configured for scanning")
            return {
                'success': True,
                'sources_queued': 0,
                'message': 'No sources to scan',
                'timestamp': datetime.utcnow().isoformat()
            }

        logger.info(f"📋 Queueing {len(source_urls)} sources for scanning")

        # Queue individual source scans with staggered timing to distribute load
        queued_tasks = []
        for i, source_url in enumerate(source_urls):
            # Stagger tasks: 0, 30s, 60s, 90s, etc.
            countdown = i * 30

            task_result = scan_single_source_task.apply_async(
                args=[source_url],
                kwargs={'priority': 5},
                queue='normal',
                countdown=countdown,
                priority=5
            )

            queued_tasks.append({
                'task_id': task_result.id,
                'source_url': source_url,
                'countdown': countdown
            })

            logger.debug(f"📤 Queued {source_url} for scan in {countdown}s")

        logger.info(
            f"✅ Scheduled scan trigger completed: {len(queued_tasks)} sources queued "
            f"over {(len(source_urls) - 1) * 30}s"
        )

        return {
            'success': True,
            'sources_queued': len(queued_tasks),
            'total_duration_seconds': (len(source_urls) - 1) * 30,
            'queued_tasks': queued_tasks,
            'timestamp': datetime.utcnow().isoformat()
        }

    except Exception as exc:
        logger.error(f"💥 Scheduled scan trigger failed: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(bind=True, base=CallbackTask, name='celery_app.tasks.cleanup_old_articles_task')
def cleanup_old_articles_task(self, days_to_keep: int = 30) -> Dict[str, Any]:
    """
    Low priority maintenance task to clean up old articles.
    Runs weekly to prevent database bloat.
    """
    try:
        logger.info(f"🧹 Starting cleanup of articles older than {days_to_keep} days")

        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Ensure database connection
            loop.run_until_complete(ensure_database_connection())

            # Get count before deletion
            old_count = loop.run_until_complete(
                article_repository.count_articles_before_date(cutoff_date)
            )

            if old_count == 0:
                logger.info("No old articles found for cleanup")
                return {
                    'success': True,
                    'articles_deleted': 0,
                    'message': 'No articles to clean up',
                    'timestamp': datetime.utcnow().isoformat()
                }

            # Delete old articles
            deleted_count = loop.run_until_complete(
                article_repository.delete_articles_before_date(cutoff_date)
            )

            logger.info(f"✅ Cleanup completed: {deleted_count} articles deleted")

            return {
                'success': True,
                'articles_deleted': deleted_count,
                'cutoff_date': cutoff_date.isoformat(),
                'days_to_keep': days_to_keep,
                'timestamp': datetime.utcnow().isoformat()
            }

        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"💥 Cleanup task failed: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'timestamp': datetime.utcnow().isoformat()
        }


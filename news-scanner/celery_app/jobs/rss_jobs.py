"""
RSS scanning and source management tasks.
"""

import logging
import asyncio
from typing import Dict, Any
from datetime import datetime

from ..celery_worker import celery_app
from .base_task import CallbackTask, ensure_database_connection

# Import existing scanner functionality
from scanner.scanner import scan_single_source
from database.sources import source_repository

logger = logging.getLogger(__name__)


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


@celery_app.task(bind=True, base=CallbackTask, name='celery_app.tasks.scan_single_source_task', priority=5)
def scan_single_source_task(self, source_url: str, source_name: str = None, priority: int = 5) -> Dict[str, Any]:
    """
    Unified task for scanning individual RSS sources.
    - Priority 5: Scheduled scans (normal priority)
    - Priority 10: Manual refresh (high priority)
    """
    try:
        # Priority-based logging
        if priority >= 8:
            logger.info(f"🔄 Manual refresh requested for source: {source_url}")
        else:
            logger.info(f"📡 Scanning RSS source: {source_url}")

        # Run the async scanner in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Ensure database connection
            loop.run_until_complete(ensure_database_connection())

            # Use provided source_name or get from database
            if not source_name:
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

                # Trigger summary jobs for new articles
                new_articles_count = len(result.new_articles)
                if new_articles_count > 0:
                    logger.info(f"📝 Triggering summary jobs for {new_articles_count} new articles from {source_name}")
                    _trigger_summary_jobs_for_new_articles(result.new_articles)

                return {
                    'success': True,
                    'source_name': source_name,
                    'source_url': source_url,
                    'scanned': result.stats.scanned,
                    'total': result.stats.total,
                    'failed': result.stats.failed,
                    'failure_rate': result.stats.failure_rate,
                    'high_failure_rate': result.has_high_failure_rate,
                    'new_articles': new_articles_count,
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

def _trigger_summary_jobs_for_new_articles(new_articles: list[Dict[str, Any]]) -> None:
    """
    Trigger summary generation and embedding jobs for newly created articles.

    Args:
        new_articles: List of article data for newly created articles
    """
    try:
        # Import the required tasks
        from .summary_jobs import generate_article_summary_task
        from ..tasks import generate_article_embedding, process_new_article

        # Queue summary, embedding, and topic analysis tasks for each new article
        for article in new_articles:
            article_url = article.get('url')
            if article_url:
                try:
                    # Queue summary task (priority 4 - after scanning)
                    summary_result = generate_article_summary_task.apply_async(
                        args=[article_url],
                        queue='llm_queue',  # Fixed: Use correct queue for summary tasks
                        priority=4  # Medium priority for summaries
                    )
                    logger.info(f"📝 Queued summary job for new article: {article_url} (task: {summary_result.id})")

                    # Queue embedding task (priority 3 - for ML processing)
                    embedding_result = generate_article_embedding.apply_async(
                        args=[article_url],
                        queue='ml_queue',  # Fixed: Use correct queue for embedding tasks
                        priority=3  # Lower priority for embeddings
                    )
                    logger.info(f"🧠 Queued embedding job for new article: {article_url} (task: {embedding_result.id})")

                    # Queue topic analysis task (priority 2 - lowest priority, runs after embedding)
                    topic_result = process_new_article.apply_async(
                        args=[article_url],
                        queue='ml_queue',  # Use ML queue for topic analysis
                        priority=2  # Lowest priority, runs after embedding
                    )
                    logger.info(f"🔍 Queued topic analysis job for new article: {article_url} (task: {topic_result.id})")

                except Exception as e:
                    logger.error(f"❌ Failed to queue processing jobs for {article_url}: {e}")

    except ImportError as e:
        logger.warning(f"Cannot trigger processing jobs - required modules not available: {e}")
    except Exception as e:
        logger.error(f"❌ Error triggering processing jobs: {e}")

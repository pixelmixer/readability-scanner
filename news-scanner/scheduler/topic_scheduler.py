"""
Topic analysis maintenance scheduler with periodic tasks.
"""

import logging
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Import tasks locally to avoid circular imports

logger = logging.getLogger(__name__)


class TopicAnalysisScheduler:
    """Scheduler for topic analysis maintenance tasks."""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False
        self.logger = logging.getLogger(__name__)

    def start(self):
        """Start the topic analysis scheduler."""
        try:
            if self.is_running:
                self.logger.warning("Topic analysis scheduler is already running")
                return

            # Add maintenance jobs
            self._add_maintenance_jobs()

            # Start the scheduler
            self.scheduler.start()
            self.is_running = True

            self.logger.info("✅ Topic Analysis Scheduler started")
            self.logger.info("📅 Maintenance schedule:")
            self.logger.info("  - Embedding generation: Every 2 hours")
            self.logger.info("  - Topic grouping: Daily at 2 AM")
            self.logger.info("  - Summary generation: Daily at 3 AM")

        except Exception as e:
            self.logger.error(f"Failed to start topic analysis scheduler: {e}")
            raise

    def stop(self):
        """Stop the topic analysis scheduler."""
        try:
            if not self.is_running:
                self.logger.warning("Topic analysis scheduler is not running")
                return

            self.scheduler.shutdown(wait=True)
            self.is_running = False
            self.logger.info("🔄 Topic Analysis Scheduler stopped")

        except Exception as e:
            self.logger.error(f"Error stopping topic analysis scheduler: {e}")

    def _add_maintenance_jobs(self):
        """Add all maintenance jobs to the scheduler."""

        # 1. Embedding generation - every 2 hours
        self.scheduler.add_job(
            self._run_embedding_generation,
            CronTrigger(hour="*/2", minute=0),  # Every 2 hours at the top of the hour
            id='topic_embedding_generation',
            name='Generate Missing Embeddings',
            replace_existing=True,
            max_instances=1
        )

        # 2. Topic grouping - daily at 2 AM
        self.scheduler.add_job(
            self._run_topic_grouping,
            CronTrigger(hour=2, minute=0),  # Daily at 2 AM
            id='topic_grouping',
            name='Group Articles by Topics',
            replace_existing=True,
            max_instances=1
        )

        # 3. Summary generation - daily at 3 AM (after topic grouping)
        self.scheduler.add_job(
            self._run_summary_generation,
            CronTrigger(hour=3, minute=0),  # Daily at 3 AM
            id='topic_summary_generation',
            name='Generate Shared Summaries',
            replace_existing=True,
            max_instances=1
        )

        # 4. Cleanup old topic groups - weekly on Sunday at 4 AM
        self.scheduler.add_job(
            self._run_topic_cleanup,
            CronTrigger(day_of_week=6, hour=4, minute=0),  # Sunday at 4 AM
            id='topic_cleanup',
            name='Cleanup Old Topic Groups',
            replace_existing=True,
            max_instances=1
        )

    async def _run_embedding_generation(self):
        """Run embedding generation for articles that don't have them."""
        try:
            self.logger.info("🔍 Starting scheduled embedding generation...")

            # Import task locally to avoid circular imports
            from celery_app.tasks import batch_generate_embeddings

            # Queue the task with proper priority
            result = batch_generate_embeddings.apply_async(
                args=[100],
                queue='normal',
                priority=3  # Same as scheduled summary tasks
            )

            self.logger.info(f"✓ Embedding generation task queued: {result.id}")

        except Exception as e:
            self.logger.error(f"Failed to queue embedding generation: {e}")

    async def _run_topic_grouping(self):
        """Run topic grouping for all articles with embeddings."""
        try:
            self.logger.info("📊 Starting scheduled topic grouping...")

            # Import task locally to avoid circular imports
            from celery_app.tasks import group_articles_by_topics

            # Queue the task with proper priority
            result = group_articles_by_topics.apply_async(
                args=[0.75, 2],
                queue='normal',
                priority=2  # Lower than embeddings
            )

            self.logger.info(f"✓ Topic grouping task queued: {result.id}")

        except Exception as e:
            self.logger.error(f"Failed to queue topic grouping: {e}")

    async def _run_summary_generation(self):
        """Run shared summary generation for all topic groups."""
        try:
            self.logger.info("📝 Starting scheduled summary generation...")

            # Import task locally to avoid circular imports
            from celery_app.tasks import generate_shared_summaries

            # Queue the task with proper priority
            result = generate_shared_summaries.apply_async(
                args=[],
                queue='normal',
                priority=2  # Lower than embeddings
            )

            self.logger.info(f"✓ Summary generation task queued: {result.id}")

        except Exception as e:
            self.logger.error(f"Failed to queue summary generation: {e}")

    async def _run_topic_cleanup(self):
        """Cleanup old topic groups to prevent database bloat."""
        try:
            self.logger.info("🧹 Starting scheduled topic cleanup...")

            # Import here to avoid circular imports
            from database.connection import db_manager

            db = db_manager.get_database()
            topics_collection = db["article_topics"]

            # Delete topic groups older than 30 days
            cutoff_date = datetime.utcnow() - timedelta(days=30)

            result = await topics_collection.delete_many({
                "created_at": {"$lt": cutoff_date}
            })

            deleted_count = result.deleted_count
            self.logger.info(f"✓ Cleaned up {deleted_count} old topic groups")

        except Exception as e:
            self.logger.error(f"Failed to cleanup topic groups: {e}")

    def get_status(self) -> dict:
        """Get scheduler status information."""
        if not self.is_running:
            return {"running": False}

        jobs_info = []
        for job in self.scheduler.get_jobs():
            jobs_info.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "next_run_human": job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else None
            })

        return {
            "running": self.is_running,
            "jobs": jobs_info
        }


# Global scheduler instance
topic_scheduler = TopicAnalysisScheduler()


def start_topic_scheduler():
    """Start the global topic analysis scheduler."""
    topic_scheduler.start()


def stop_topic_scheduler():
    """Stop the global topic analysis scheduler."""
    topic_scheduler.stop()

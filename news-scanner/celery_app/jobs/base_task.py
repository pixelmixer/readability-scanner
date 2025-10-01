"""
Base task classes and utilities for Celery jobs.
"""

import logging
import asyncio
from celery import Task
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

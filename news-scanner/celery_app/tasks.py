"""
Celery tasks for RSS scanning and article processing.

This module imports and registers all tasks from individual job files.
Each job type is organized in its own module for better maintainability.
"""

# Import all task modules to register them with Celery
from .jobs import base_task
from .jobs import rss_jobs
from .jobs import summary_jobs
from .jobs import backfill_jobs
from .jobs import reddit_jobs

# Re-export commonly used utilities for backward compatibility
from .jobs.base_task import CallbackTask, ensure_database_connection

# Re-export all task functions for direct import by API routes
from .jobs.rss_jobs import (
    manual_refresh_source_task,
    scan_single_source_task,
    scheduled_scan_trigger_task
)
from .jobs.summary_jobs import (
    generate_article_summary_task,
    process_summary_backlog_task,
    manual_summary_trigger_task
)
from .jobs.backfill_jobs import (
    backfill_publication_dates_task,
    cleanup_old_date_fields_task
)
from .jobs.reddit_jobs import (
    reddit_backfill_task,
    reddit_backfill_stats_task
)

# Import the Celery app for any additional configuration
from celery_app.celery_worker import celery_app

# All tasks are now automatically registered through the imports above
# Task names remain the same for backward compatibility:
# - celery_app.tasks.manual_refresh_source_task
# - celery_app.tasks.scan_single_source_task
# - celery_app.tasks.scheduled_scan_trigger_task
# - celery_app.tasks.generate_article_summary_task
# - celery_app.tasks.process_summary_backlog_task
# - celery_app.tasks.manual_summary_trigger_task
# - celery_app.tasks.backfill_publication_dates_task
# - celery_app.tasks.cleanup_old_date_fields_task
# - celery_app.tasks.reddit_backfill_task
# - celery_app.tasks.reddit_backfill_stats_task
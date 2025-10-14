"""
Celery tasks for RSS scanning and article processing.

This module imports and registers all tasks from individual job files.
Each job type is organized in its own module for better maintainability.
"""

# Import all task modules to register them with Celery
from .jobs import base_task
from .jobs import rss_jobs
from .jobs import summary_jobs
from .jobs import summary_embedding_jobs
from .jobs import backfill_jobs
from .jobs import reddit_jobs
from .jobs import topic_analysis_jobs_ml
from .jobs import daily_topics_jobs

# Re-export commonly used utilities for backward compatibility
from .jobs.base_task import CallbackTask as BaseTask, ensure_database_connection

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
from .jobs.summary_embedding_jobs import (
    generate_summary_embedding_task,
    batch_generate_summary_embeddings_task
)
from .jobs.backfill_jobs import (
    backfill_publication_dates_task,
    cleanup_old_date_fields_task
)
from .jobs.reddit_jobs import (
    reddit_backfill_task,
    reddit_backfill_stats_task
)
# Import topic analysis functions from ML service jobs
from .jobs.topic_analysis_jobs_ml import (
    generate_article_embedding_sync as _generate_article_embedding,
    batch_generate_embeddings_sync as _batch_generate_embeddings,
    group_articles_by_topics_sync as _group_articles_by_topics,
    generate_shared_summaries_sync as _generate_shared_summaries,
    process_new_article_sync as _process_new_article,
    full_topic_analysis_pipeline_sync as _full_topic_analysis_pipeline
)
# Import daily topics functions
from .jobs.daily_topics_jobs import (
    generate_daily_topics_sync as _generate_daily_topics,
    regenerate_daily_topics_sync as _regenerate_daily_topics
)

# Import the Celery app for any additional configuration
from celery_app.celery_worker import celery_app

# Register topic analysis tasks as Celery tasks
@celery_app.task(bind=True, base=BaseTask, name='celery_app.tasks.generate_article_embedding', priority=3)
def generate_article_embedding(self, article_url: str):
    """Celery task wrapper for generate_article_embedding. Priority 3 (lowest priority for embeddings)."""
    # Run the synchronous wrapper function
    return _generate_article_embedding(article_url)

@celery_app.task(bind=True, base=BaseTask, name='celery_app.tasks.batch_generate_embeddings', priority=3)
def batch_generate_embeddings(self, batch_size: int = 100):
    """Celery task wrapper for batch_generate_embeddings. Priority 3 (same as scheduled summary tasks)."""
    # Run the synchronous wrapper function
    return _batch_generate_embeddings(batch_size)

@celery_app.task(bind=True, base=BaseTask, name='celery_app.tasks.group_articles_by_topics', priority=2)
def group_articles_by_topics(self, similarity_threshold: float = 0.75, min_group_size: int = 2):
    """Celery task wrapper for group_articles_by_topics. Priority 2 (lower than embeddings)."""
    # Run the synchronous wrapper function
    return _group_articles_by_topics(similarity_threshold, min_group_size)

@celery_app.task(bind=True, base=BaseTask, name='celery_app.tasks.generate_shared_summaries', priority=2)
def generate_shared_summaries(self):
    """Celery task wrapper for generate_shared_summaries. Priority 2 (lower than embeddings)."""
    # Run the synchronous wrapper function
    return _generate_shared_summaries()

@celery_app.task(bind=True, base=BaseTask, name='celery_app.tasks.process_new_article', priority=4)
def process_new_article(self, article_url: str):
    """Celery task wrapper for process_new_article. Priority 4 (higher than summary tasks)."""
    # Run the synchronous wrapper function
    return _process_new_article(article_url)

@celery_app.task(bind=True, base=BaseTask, name='celery_app.tasks.full_topic_analysis_pipeline', priority=1)
def full_topic_analysis_pipeline(self):
    """Celery task wrapper for full_topic_analysis_pipeline. Priority 1 (lowest, for maintenance)."""
    # Run the synchronous wrapper function
    return _full_topic_analysis_pipeline()

@celery_app.task(bind=True, base=BaseTask, name='celery_app.tasks.generate_daily_topics_task', priority=2)
def generate_daily_topics_task(self):
    """Celery task wrapper for generate_daily_topics. Priority 2 (low, scheduled maintenance)."""
    # Run the synchronous wrapper function
    return _generate_daily_topics()

@celery_app.task(bind=True, base=BaseTask, name='celery_app.tasks.regenerate_daily_topics_task', priority=10)
def regenerate_daily_topics_task(self):
    """Celery task wrapper for regenerate_daily_topics. Priority 10 (highest, user-initiated)."""
    # Run the synchronous wrapper function
    return _regenerate_daily_topics()

# All tasks are now automatically registered through the imports above
# Task names remain the same for backward compatibility:
# - celery_app.tasks.manual_refresh_source_task
# - celery_app.tasks.scan_single_source_task
# - celery_app.tasks.scheduled_scan_trigger_task
# - celery_app.tasks.generate_article_summary_task
# - celery_app.tasks.process_summary_backlog_task
# - celery_app.tasks.manual_summary_trigger_task
# - celery_app.tasks.generate_summary_embedding_task
# - celery_app.tasks.batch_generate_summary_embeddings_task
# - celery_app.tasks.backfill_publication_dates_task
# - celery_app.tasks.cleanup_old_date_fields_task
# - celery_app.tasks.reddit_backfill_task
# - celery_app.tasks.reddit_backfill_stats_task
# - celery_app.tasks.generate_article_embedding
# - celery_app.tasks.batch_generate_embeddings
# - celery_app.tasks.group_articles_by_topics
# - celery_app.tasks.generate_shared_summaries
# - celery_app.tasks.process_new_article
# - celery_app.tasks.full_topic_analysis_pipeline
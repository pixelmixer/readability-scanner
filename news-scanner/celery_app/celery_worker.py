"""
Celery application configuration and worker setup.
"""

import logging
import os
from celery import Celery
from celery.schedules import crontab

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Redis connection URL
REDIS_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')

# Create Celery instance
celery_app = Celery(
    'news-scanner',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['celery_app.tasks']
)

# Celery configuration
celery_app.conf.update(
    # Task routing - assign tasks to specific queues
    task_routes={
        'celery_app.tasks.manual_refresh_source_task': {'queue': 'high'},
        'celery_app.tasks.scan_single_source_task': {'queue': 'normal'},
        'celery_app.tasks.scan_article_task': {'queue': 'normal'},
        'celery_app.tasks.scheduled_scan_trigger_task': {'queue': 'low'},
        'celery_app.tasks.cleanup_old_articles_task': {'queue': 'low'},
    },

    # Task priority settings
    task_inherit_parent_priority=True,
    task_default_priority=5,

    # Worker settings
    worker_prefetch_multiplier=1,  # Prevent worker from hoarding tasks
    task_acks_late=True,          # Acknowledge tasks after completion
    worker_max_tasks_per_child=50, # Restart worker after 50 tasks (prevent memory leaks)

    # Result backend settings
    result_expires=3600,          # Results expire after 1 hour
    result_backend_transport_options={'visibility_timeout': 3600},

    # Task execution settings
    task_time_limit=30 * 60,      # Hard time limit: 30 minutes
    task_soft_time_limit=25 * 60, # Soft time limit: 25 minutes
    task_max_retries=3,           # Maximum retry attempts
    task_default_retry_delay=60,  # Default retry delay: 1 minute

    # Schedule for periodic tasks (replaces cron)
    beat_schedule={
        # Trigger source scanning every 6 hours
        'scheduled-source-scan': {
            'task': 'celery_app.tasks.scheduled_scan_trigger_task',
            'schedule': crontab(minute=0, hour='*/6'),  # Every 6 hours
            'options': {'queue': 'low', 'priority': 3}
        },

        # Clean up old articles weekly
        'cleanup-old-articles': {
            'task': 'celery_app.tasks.cleanup_old_articles_task',
            'schedule': crontab(minute=0, hour=2, day_of_week=0),  # Sunday 2 AM
            'options': {'queue': 'low', 'priority': 1}
        },

        # Process summary backlog every 2 hours
        'process-summary-backlog': {
            'task': 'celery_app.tasks.process_summary_backlog_task',
            'schedule': crontab(minute=0, hour='*/2'),  # Every 2 hours
            'options': {'queue': 'low', 'priority': 2}
        },
    },

    # Timezone
    timezone='UTC',

    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# Import tasks to register them
from celery_app import tasks

logger.info("🚀 Celery application configured successfully")
logger.info(f"📡 Redis broker: {REDIS_URL}")
logger.info("📋 Task queues: high (manual), normal (automatic), low (maintenance)")


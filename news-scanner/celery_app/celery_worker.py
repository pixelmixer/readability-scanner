"""
Celery application configuration and worker setup.
"""

import logging
import os
from celery import Celery
from celery.schedules import crontab

# Configure logging first
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Set up OpenTelemetry logging for Celery
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# Set up OpenTelemetry for Celery (only if not already set)
if not trace.get_tracer_provider() or isinstance(trace.get_tracer_provider(), trace.NoOpTracerProvider):
    trace.set_tracer_provider(TracerProvider())

tracer = trace.get_tracer(__name__)

# Configure OTLP exporter for traces
otlp_exporter = OTLPSpanExporter(
    endpoint="http://host.docker.internal:30007",
    insecure=True
)

# Add span processor only if tracer provider supports it
try:
    tracer_provider = trace.get_tracer_provider()
    if hasattr(tracer_provider, 'add_span_processor'):
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)
    else:
        logger.warning("Tracer provider does not support add_span_processor, skipping OTLP configuration")
except Exception as e:
    logger.warning(f"Failed to configure OpenTelemetry span processor: {e}")

# Set up OpenTelemetry logging bridge AFTER logger is configured
LoggingInstrumentor().instrument()

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
        'celery_app.tasks.cleanup_old_date_fields_task': {'queue': 'high'},
        'celery_app.tasks.backfill_publication_dates_task': {'queue': 'low'},
        'celery_app.tasks.reddit_backfill_task': {'queue': 'low'},
        'celery_app.tasks.reddit_backfill_stats_task': {'queue': 'low'},
        # Topic analysis tasks
        'celery_app.tasks.generate_article_embedding': {'queue': 'normal'},
        'celery_app.tasks.batch_generate_embeddings': {'queue': 'low'},
        'celery_app.tasks.group_articles_by_topics': {'queue': 'low'},
        'celery_app.tasks.generate_shared_summaries': {'queue': 'low'},
        'celery_app.tasks.process_new_article': {'queue': 'normal'},
        'celery_app.tasks.full_topic_analysis_pipeline': {'queue': 'low'},
        # Daily topics tasks
        'celery_app.tasks.generate_daily_topics_task': {'queue': 'low'},
        'celery_app.tasks.regenerate_daily_topics_task': {'queue': 'high'},
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
    task_max_retries=3,           # Maximum retry attempts
    task_default_retry_delay=60,  # Default retry delay: 1 minute

    # Schedule for periodic tasks (replaces cron)
    beat_schedule={
        # Trigger source scanning every 6 hours
        'scheduled-source-scan': {
            'task': 'celery_app.tasks.scheduled_scan_trigger_task',
            'schedule': crontab(minute=0, hour='*/1'),  # Every 1 hour
            'options': {'queue': 'low', 'priority': 3}
        },

        # Process summary backlog every 30 minutes
        'process-summary-backlog': {
            'task': 'celery_app.tasks.process_summary_backlog_task',
            'schedule': crontab(minute='*/30'),  # Every 30 minutes
            'options': {'queue': 'low', 'priority': 2}
        },

        # Full topic analysis pipeline - weekly on Sundays at 2 AM
        'weekly-topic-analysis': {
            'task': 'celery_app.tasks.full_topic_analysis_pipeline',
            'schedule': crontab(minute=0, hour=2, day_of_week=0),  # Sunday 2 AM
            'options': {'queue': 'low', 'priority': 1}
        },

        # Daily topics generation - hourly
        'hourly-daily-topics-update': {
            'task': 'celery_app.tasks.generate_daily_topics_task',
            'schedule': crontab(minute=0, hour='*'),  # Every hour on the hour
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


"""
Summary embedding generation tasks.
"""

import logging
import asyncio
from typing import Dict, Any, List
from datetime import datetime

from ..celery_worker import celery_app
from .base_task import CallbackTask, ensure_database_connection

# Import existing services
from database.articles import article_repository
from services.ml_client import ml_client
from database.connection import db_manager

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=CallbackTask, name='celery_app.tasks.generate_summary_embedding_task', priority=4)
def generate_summary_embedding_task(self, article_url: str) -> Dict[str, Any]:
    """
    Generate an embedding from the article's summary.
    This task runs after a summary has been successfully generated.
    """
    try:
        logger.info(f"🧠 Generating summary embedding for article: {article_url}")

        # Run the async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Ensure database connection
            loop.run_until_complete(ensure_database_connection())

            # Get the article
            article = loop.run_until_complete(
                article_repository.get_article_by_url(article_url)
            )

            if not article:
                logger.error(f"Article not found: {article_url}")
                return {
                    'success': False,
                    'article_url': article_url,
                    'error': 'Article not found',
                    'timestamp': datetime.utcnow().isoformat()
                }

            # Check if article has a completed summary
            if not article.summary or article.summary_processing_status != "completed":
                logger.warning(f"Article does not have a completed summary: {article_url}")
                return {
                    'success': False,
                    'article_url': article_url,
                    'error': 'No completed summary available',
                    'timestamp': datetime.utcnow().isoformat()
                }

            # Check if summary embedding already exists
            db = db_manager.get_database()
            collection = db["documents"]
            existing = loop.run_until_complete(
                collection.find_one({"url": article_url, "summary_embedding": {"$exists": True}})
            )

            if existing and existing.get("summary_embedding"):
                logger.info(f"Summary embedding already exists: {article_url}")
                return {
                    'success': True,
                    'article_url': article_url,
                    'status': 'already_completed',
                    'timestamp': datetime.utcnow().isoformat()
                }

            # Generate embedding from summary via ML service (synchronous version for Celery)
            summary_text = article.summary
            embedding = ml_client.generate_summary_embedding_sync(summary_text, article_url)

            if embedding is None:
                logger.error(f"Failed to generate summary embedding: {article_url}")
                return {
                    'success': False,
                    'article_url': article_url,
                    'error': 'Failed to generate embedding via ML service',
                    'timestamp': datetime.utcnow().isoformat()
                }

            # Store embedding in database
            result = loop.run_until_complete(
                collection.update_one(
                    {"url": article_url},
                    {
                        "$set": {
                            "summary_embedding": embedding,
                            "summary_embedding_updated_at": datetime.utcnow(),
                            "summary_embedding_model": "all-MiniLM-L6-v2"
                        }
                    }
                )
            )

            if result.modified_count == 0:
                logger.warning(f"Failed to store summary embedding in database: {article_url}")
                return {
                    'success': False,
                    'article_url': article_url,
                    'error': 'Failed to store embedding in database',
                    'timestamp': datetime.utcnow().isoformat()
                }

            logger.info(f"✅ Summary embedding generated successfully for: {article_url}")
            return {
                'success': True,
                'article_url': article_url,
                'embedding_dimension': len(embedding),
                'timestamp': datetime.utcnow().isoformat()
            }

        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"💥 Summary embedding generation task failed for {article_url}: {exc}")

        # Retry up to 2 times
        if self.request.retries < 2:
            logger.info(f"🔄 Retrying summary embedding generation for {article_url} (attempt {self.request.retries + 1}/2)")
            raise self.retry(exc=exc, countdown=60, max_retries=2)

        return {
            'success': False,
            'article_url': article_url,
            'error': str(exc),
            'retries_exceeded': True,
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(bind=True, base=CallbackTask, name='celery_app.tasks.batch_generate_summary_embeddings_task')
def batch_generate_summary_embeddings_task(self, batch_size: int = 50) -> Dict[str, Any]:
    """
    Generate summary embeddings for articles that have summaries but no summary embeddings.
    This task runs periodically to process the backlog.
    """
    try:
        logger.info(f"📚 Processing summary embedding backlog (batch size: {batch_size})")

        # Run the async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Ensure database connection
            loop.run_until_complete(ensure_database_connection())

            # Get articles with summaries but no summary embeddings
            db = db_manager.get_database()
            collection = db["documents"]

            # Query for articles with completed summaries but no summary_embedding
            cursor = collection.find(
                {
                    "summary": {"$exists": True, "$ne": None, "$ne": ""},
                    "summary_processing_status": "completed",
                    "summary_embedding": {"$exists": False}
                },
                {"url": 1, "title": 1, "summary": 1}
            ).limit(batch_size)

            articles = loop.run_until_complete(cursor.to_list(length=batch_size))
            logger.info(f"📋 Retrieved {len(articles)} articles needing summary embeddings")

            if not articles:
                logger.info("No articles found that need summary embeddings")
                return {
                    'success': True,
                    'articles_processed': 0,
                    'message': 'No articles need summary embeddings',
                    'timestamp': datetime.utcnow().isoformat()
                }

            logger.info(f"Found {len(articles)} articles needing summary embeddings")

            # Queue individual summary embedding tasks
            queued_tasks = []
            for article in articles:
                task_result = generate_summary_embedding_task.apply_async(
                    args=[article['url']],
                    queue='ml_queue',
                    priority=4  # Same priority as summary generation
                )

                queued_tasks.append({
                    'task_id': task_result.id,
                    'article_url': article['url'],
                    'article_title': article.get('title', '')
                })

                logger.debug(f"📤 Queued summary embedding generation for: {article.get('title', article['url'])}")

            logger.info(f"✅ Queued {len(queued_tasks)} summary embedding generation tasks")

            return {
                'success': True,
                'articles_queued': len(queued_tasks),
                'queued_tasks': queued_tasks,
                'timestamp': datetime.utcnow().isoformat()
            }

        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"💥 Summary embedding backlog processing failed: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'timestamp': datetime.utcnow().isoformat()
        }


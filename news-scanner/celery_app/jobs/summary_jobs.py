"""
Article summary generation tasks.
"""

import logging
import asyncio
from typing import Dict, Any
from datetime import datetime

from ..celery_worker import celery_app
from .base_task import CallbackTask, ensure_database_connection

# Import existing services
from database.articles import article_repository
from services.summary_service import summary_service

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=CallbackTask, name='celery_app.tasks.generate_article_summary_task', priority=4)
def generate_article_summary_task(self, article_url: str) -> Dict[str, Any]:
    """
    Generate a summary for a single article.
    This task processes one article at a time to avoid overwhelming the LLM API.
    """
    try:
        logger.info(f"📝 Generating summary for article: {article_url}")

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

            # Check if article already has a summary
            if article.summary and article.summary_processing_status == "completed":
                logger.info(f"Article already has summary: {article_url}")
                return {
                    'success': True,
                    'article_url': article_url,
                    'summary': article.summary,
                    'status': 'already_completed',
                    'timestamp': datetime.utcnow().isoformat()
                }

            # Mark as processing
            loop.run_until_complete(
                article_repository.update_article_summary(
                    article_url, "", "", "", "processing"
                )
            )

            # Prepare content for summary generation
            content = article.cleaned_data or article.content or ""
            if not content.strip():
                logger.warning(f"No content available for summary: {article_url}")
                loop.run_until_complete(
                    article_repository.update_article_summary(
                        article_url, "", "", "", "failed", "No content available"
                    )
                )
                return {
                    'success': False,
                    'article_url': article_url,
                    'error': 'No content available for summary',
                    'timestamp': datetime.utcnow().isoformat()
                }

            # Generate summary
            summary_result = loop.run_until_complete(
                summary_service.generate_summary(content, article.title)
            )

            if summary_result["success"]:
                # Update article with summary
                update_success = loop.run_until_complete(
                    article_repository.update_article_summary(
                        article_url,
                        summary_result["summary"],
                        summary_result["model"],
                        summary_result["prompt_version"],
                        "completed"
                    )
                )

                if update_success:
                    logger.info(f"✅ Summary generated successfully for: {article_url}")

                    # Queue summary embedding generation task
                    try:
                        from .summary_embedding_jobs import generate_summary_embedding_task
                        embedding_task_result = generate_summary_embedding_task.apply_async(
                            args=[article_url],
                            queue='ml_queue',
                            priority=4  # Same priority as summary generation
                        )
                        logger.info(f"🧠 Queued summary embedding generation for: {article_url} (task: {embedding_task_result.id})")
                    except Exception as e:
                        logger.warning(f"Failed to queue summary embedding generation for {article_url}: {e}")

                    return {
                        'success': True,
                        'article_url': article_url,
                        'summary': summary_result["summary"],
                        'model': summary_result["model"],
                        'prompt_version': summary_result["prompt_version"],
                        'timestamp': datetime.utcnow().isoformat()
                    }
                else:
                    logger.error(f"Failed to update article with summary: {article_url}")
                    return {
                        'success': False,
                        'article_url': article_url,
                        'error': 'Failed to update article with summary',
                        'timestamp': datetime.utcnow().isoformat()
                    }
            else:
                # Mark as failed
                loop.run_until_complete(
                    article_repository.update_article_summary(
                        article_url, "", "", "", "failed", summary_result["error"]
                    )
                )

                logger.error(f"Summary generation failed for {article_url}: {summary_result['error']}")
                return {
                    'success': False,
                    'article_url': article_url,
                    'error': summary_result["error"],
                    'timestamp': datetime.utcnow().isoformat()
                }

        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"💥 Summary generation task failed for {article_url}: {exc}")

        # Mark as failed in database
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(ensure_database_connection())
            loop.run_until_complete(
                article_repository.update_article_summary(
                    article_url, "", "", "", "failed", str(exc)
                )
            )
            loop.close()
        except Exception as db_exc:
            logger.error(f"Failed to update article status in database: {db_exc}")

        # Retry up to 2 times for summary generation
        if self.request.retries < 2:
            logger.info(f"🔄 Retrying summary generation for {article_url} (attempt {self.request.retries + 1}/2)")
            raise self.retry(exc=exc, countdown=60, max_retries=2)

        return {
            'success': False,
            'article_url': article_url,
            'error': str(exc),
            'retries_exceeded': True,
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(bind=True, base=CallbackTask, name='celery_app.tasks.process_summary_backlog_task')
def process_summary_backlog_task(self, batch_size: int = 10) -> Dict[str, Any]:
    """
    Process a batch of articles that need summaries.
    This task runs periodically to work through the backlog.
    """
    try:
        logger.info(f"📚 Processing summary backlog (batch size: {batch_size})")

        # Run the async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Ensure database connection
            loop.run_until_complete(ensure_database_connection())

            # Debug: Check total count first
            total_count = loop.run_until_complete(
                article_repository.count_articles_without_summaries()
            )
            logger.info(f"📊 Total articles without summaries: {total_count}")

            # Get articles without summaries
            articles = loop.run_until_complete(
                article_repository.get_articles_without_summaries(limit=batch_size)
            )
            logger.info(f"📋 Retrieved {len(articles)} articles from database")

            if not articles:
                logger.info("No articles found that need summaries")
                return {
                    'success': True,
                    'articles_processed': 0,
                    'message': 'No articles need summaries',
                    'timestamp': datetime.utcnow().isoformat()
                }

            logger.info(f"Found {len(articles)} articles needing summaries")

            # Queue individual summary tasks
            queued_tasks = []
            for article in articles:
                task_result = generate_article_summary_task.apply_async(
                    args=[str(article.url)],
                    queue='llm_queue',
                    priority=3  # Lower priority than RSS scanning
                )

                queued_tasks.append({
                    'task_id': task_result.id,
                    'article_url': str(article.url),
                    'article_title': article.title
                })

                logger.debug(f"📤 Queued summary generation for: {article.title}")

            logger.info(f"✅ Queued {len(queued_tasks)} summary generation tasks")

            return {
                'success': True,
                'articles_queued': len(queued_tasks),
                'queued_tasks': queued_tasks,
                'timestamp': datetime.utcnow().isoformat()
            }

        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"💥 Summary backlog processing failed: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(bind=True, base=CallbackTask, name='celery_app.tasks.manual_summary_trigger_task')
def manual_summary_trigger_task(self, batch_size: int = 50) -> Dict[str, Any]:
    """
    Manually trigger summary processing for articles.
    This is called from the API when user requests summary generation.
    """
    try:
        logger.info(f"🚀 Manual summary trigger requested (batch size: {batch_size})")

        # Run the async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Ensure database connection
            loop.run_until_complete(ensure_database_connection())

            # Get summary statistics
            stats = loop.run_until_complete(
                article_repository.get_summary_statistics()
            )

            # Process the backlog
            result = process_summary_backlog_task.apply_async(
                args=[batch_size],
                queue='llm_queue',
                priority=5  # Higher priority for manual triggers
            )

            logger.info(f"✅ Manual summary processing triggered: {stats}")

            return {
                'success': True,
                'task_id': result.id,
                'batch_size': batch_size,
                'current_stats': stats,
                'timestamp': datetime.utcnow().isoformat()
            }

        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"💥 Manual summary trigger failed: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'timestamp': datetime.utcnow().isoformat()
        }

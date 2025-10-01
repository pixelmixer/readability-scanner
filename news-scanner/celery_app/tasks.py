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
from services.date_extraction_service import date_extraction_service
from services.summary_service import summary_service

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


@celery_app.task(bind=True, base=CallbackTask, name='celery_app.tasks.generate_article_summary_task')
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
                    queue='normal',
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
                queue='normal',
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


@celery_app.task(bind=True, base=CallbackTask, name='celery_app.tasks.backfill_publication_dates_task')
def backfill_publication_dates_task(self, batch_size: int = 20) -> Dict[str, Any]:
    """
    Backfill missing publication dates for existing articles.
    This task processes articles that don't have publication dates and tries to extract them.
    """
    try:
        logger.info(f"📅 Starting publication date backfill (batch size: {batch_size})")

        # Run the async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Ensure database connection
            loop.run_until_complete(ensure_database_connection())

            # Get count of articles without publication dates
            total_count = loop.run_until_complete(
                article_repository.count_articles_without_publication_date()
            )
            logger.info(f"📊 Total articles without publication dates: {total_count}")

            if total_count == 0:
                logger.info("No articles need publication date backfill")
                return {
                    'success': True,
                    'articles_processed': 0,
                    'dates_found': 0,
                    'message': 'No articles need publication date backfill',
                    'timestamp': datetime.utcnow().isoformat()
                }

            # Get articles without publication dates
            articles = loop.run_until_complete(
                article_repository.get_articles_without_publication_date(limit=batch_size)
            )
            logger.info(f"📋 Retrieved {len(articles)} articles for date extraction")

            if not articles:
                logger.info("No articles found for date extraction")
                return {
                    'success': True,
                    'articles_processed': 0,
                    'dates_found': 0,
                    'message': 'No articles found for processing',
                    'timestamp': datetime.utcnow().isoformat()
                }

            # Process each article
            dates_found = 0
            processed_count = 0
            errors = []

            for article in articles:
                try:
                    # Convert article to dict for processing
                    article_data = {
                        'url': str(article.url),
                        'content': article.content,
                        'cleaned_data': article.cleaned_data,
                        'publication_date': article.publication_date
                    }

                    # Extract publication date
                    extracted_date = loop.run_until_complete(
                        date_extraction_service.extract_publication_date(article_data)
                    )

                    if extracted_date:
                        # Update the article with the extracted date
                        success = loop.run_until_complete(
                            article_repository.update_article_publication_date(
                                str(article.url),
                                extracted_date
                            )
                        )

                        if success:
                            dates_found += 1
                            logger.debug(f"✅ Updated publication date for {article.url}: {extracted_date}")
                        else:
                            errors.append(f"Failed to update date for {article.url}")
                    else:
                        logger.debug(f"❌ No publication date found for {article.url}")

                    processed_count += 1

                except Exception as e:
                    error_msg = f"Error processing article {article.url}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            logger.info(f"✅ Publication date backfill completed: {dates_found}/{processed_count} dates found")

            return {
                'success': True,
                'articles_processed': processed_count,
                'dates_found': dates_found,
                'errors': errors[:10],  # Limit errors to first 10
                'error_count': len(errors),
                'timestamp': datetime.utcnow().isoformat()
            }

        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"💥 Publication date backfill failed: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(bind=True, base=CallbackTask, name='celery_app.tasks.cleanup_old_date_fields_task')
def cleanup_old_date_fields_task(self, batch_size: int = 50) -> Dict[str, Any]:
    """
    One-time backfill job to remove old date field names and migrate data.

    This task:
    1. Finds documents with 'publication date' field OR 'publishedTime' field
    2. Migrates date data to 'publication_date' field with priority:
       - 'publication date' (if exists and 'publication_date' is empty)
       - 'publishedTime' (if exists and no other date field exists)
    3. Removes 'publication date' and 'publishedTime' fields
    """
    try:
        logger.info(f"🧹 Starting cleanup of old date fields (batch size: {batch_size})")

        # Run the async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Ensure database connection
            loop.run_until_complete(ensure_database_connection())

            # Get the collection directly for this migration
            collection = article_repository.collection

            # Find documents that have 'publication date' field OR 'publishedTime' field (including null values)
            query = {
                "$or": [
                    {"publication date": {"$exists": True}},
                    {"publishedTime": {"$exists": True}}
                ]
            }

            total_count = loop.run_until_complete(collection.count_documents(query))
            logger.info(f"📊 Total documents with 'publication date' or 'publishedTime' field: {total_count}")

            if total_count == 0:
                logger.info("No documents need date field cleanup")
                return {
                    'success': True,
                    'documents_processed': 0,
                    'fields_migrated': 0,
                    'fields_removed': 0,
                    'message': 'No documents need date field cleanup',
                    'timestamp': datetime.utcnow().isoformat()
                }

            # Process in batches
            processed_count = 0
            migrated_count = 0
            removed_count = 0
            errors = []

            while processed_count < total_count:
                # Get batch of documents
                cursor = collection.find(query).limit(batch_size)
                docs = loop.run_until_complete(cursor.to_list(length=batch_size))

                if not docs:
                    break

                logger.info(f"📋 Processing batch: {len(docs)} documents")

                for doc in docs:
                    try:
                        url = doc.get('url', 'unknown')
                        update_operations = {}
                        fields_to_remove = []

                        # Check if we need to migrate 'publication date' to 'publication_date'
                        old_pub_date = doc.get('publication date')
                        published_time = doc.get('publishedTime')
                        new_pub_date = doc.get('publication_date')

                        # Priority: 'publication date' > 'publishedTime' > existing 'publication_date'
                        date_to_migrate = None
                        if old_pub_date and not new_pub_date:
                            # Copy 'publication date' to 'publication_date' only if old has value and new doesn't
                            date_to_migrate = old_pub_date
                            logger.debug(f"✅ Migrating 'publication date' for {url}")
                        elif published_time and not new_pub_date and not old_pub_date:
                            # Copy 'publishedTime' to 'publication_date' if no other date field exists
                            date_to_migrate = published_time
                            logger.debug(f"✅ Migrating 'publishedTime' for {url}")
                        elif old_pub_date is None and new_pub_date:
                            # Old field is null but new field has value - just remove old field
                            logger.debug(f"✅ Old publication date field is null, keeping new field for {url}")

                        if date_to_migrate:
                            update_operations['publication_date'] = date_to_migrate
                            migrated_count += 1

                        # Mark old fields for removal
                        if 'publication date' in doc:
                            fields_to_remove.append('publication date')
                            removed_count += 1

                        if 'publishedTime' in doc:
                            fields_to_remove.append('publishedTime')
                            removed_count += 1

                        # Perform the update
                        if update_operations or fields_to_remove:
                            # Add fields to remove using $unset
                            if fields_to_remove:
                                update_operations['$unset'] = {field: "" for field in fields_to_remove}

                            # Use $set for new fields, $unset for removal
                            if '$unset' in update_operations:
                                unset_fields = update_operations.pop('$unset')
                                loop.run_until_complete(collection.update_one(
                                    {"_id": doc['_id']},
                                    {
                                        "$set": update_operations,
                                        "$unset": unset_fields
                                    }
                                ))
                            else:
                                loop.run_until_complete(collection.update_one(
                                    {"_id": doc['_id']},
                                    {"$set": update_operations}
                                ))

                        processed_count += 1

                    except Exception as e:
                        error_msg = f"Error processing document {doc.get('url', 'unknown')}: {e}"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        processed_count += 1

                logger.info(f"📈 Progress: {processed_count}/{total_count} documents processed")

            logger.info(f"✅ Date field cleanup completed: {migrated_count} date fields migrated, {removed_count} old fields removed")

            return {
                'success': True,
                'documents_processed': processed_count,
                'fields_migrated': migrated_count,
                'fields_removed': removed_count,
                'errors': errors[:10],  # Limit errors to first 10
                'error_count': len(errors),
                'timestamp': datetime.utcnow().isoformat()
            }

        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"💥 Date field cleanup failed: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'timestamp': datetime.utcnow().isoformat()
        }


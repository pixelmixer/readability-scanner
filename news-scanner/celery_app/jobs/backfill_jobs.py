"""
Data backfill and migration tasks.
"""

import logging
import asyncio
from typing import Dict, Any
from datetime import datetime

from ..celery_worker import celery_app
from .base_task import CallbackTask, ensure_database_connection

# Import existing services
from database.articles import article_repository
from services.date_extraction_service import date_extraction_service

logger = logging.getLogger(__name__)


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

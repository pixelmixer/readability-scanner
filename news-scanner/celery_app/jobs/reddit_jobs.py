"""
Reddit-specific backfill and processing tasks.
"""

import logging
import asyncio
import time
from typing import Dict, Any
from datetime import datetime

from ..celery_worker import celery_app
from .base_task import CallbackTask, ensure_database_connection

# Import existing services
from database.articles import article_repository
from scanner.rss_parser import RSSParser

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, base=CallbackTask, name='celery_app.tasks.reddit_backfill_task')
def reddit_backfill_task(self, batch_size: int = 50, skip: int = 0) -> Dict[str, Any]:
    """
    Backfill and reprocess Reddit articles with new URL extraction logic.

    This task processes Reddit articles in batches to extract the correct article URLs
    from the content field instead of using the Reddit comment link.

    Args:
        batch_size: Number of articles to process in this batch
        skip: Number of articles to skip (for pagination)

    Returns:
        Dictionary with processing results
    """
    try:
        logger.info(f"🔄 Starting Reddit backfill task (batch_size={batch_size}, skip={skip})")

        # Run the async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Ensure database connection
            loop.run_until_complete(ensure_database_connection())

            # Import RSS parser for URL extraction
            parser = RSSParser()

            # Get Reddit articles
            articles = loop.run_until_complete(
                article_repository.get_reddit_articles(limit=batch_size, skip=skip)
            )

            if not articles:
                logger.info("No Reddit articles found to process")
                return {
                    'success': True,
                    'articles_processed': 0,
                    'articles_updated': 0,
                    'message': 'No Reddit articles found',
                    'timestamp': datetime.utcnow().isoformat()
                }

            logger.info(f"Found {len(articles)} Reddit articles to process")

            # Process each article
            updated_count = 0
            errors = []

            for article in articles:
                try:
                    # Re-fetch the Reddit RSS feed to get raw content with [link] pattern
                    logger.debug(f"Re-fetching Reddit RSS for article: {article.title}")

                    # Add delay between requests to avoid rate limiting
                    time.sleep(2)  # Wait 2 seconds between requests

                    # Parse the RSS feed to get raw content
                    try:
                        feed_data = parser.parse_feed(article.origin)
                        raw_articles = feed_data.get('articles', [])
                    except Exception as e:
                        if "Too Many Requests" in str(e) or "rate limit" in str(e).lower():
                            logger.warning(f"Reddit rate limited, skipping article: {article.title}")
                            errors.append(f"Rate limited for article: {article.title}")
                            continue
                        else:
                            raise e

                    if not raw_articles:
                        logger.warning(f"No articles found in RSS feed (possibly rate limited): {article.origin}")
                        errors.append(f"No articles in RSS feed: {article.origin}")
                        continue

                    # Find the matching article in the raw RSS data
                    matching_article = None
                    for raw_article in raw_articles:
                        if raw_article.get('title') == article.title:
                            matching_article = raw_article
                            break

                    if matching_article:
                        # Create a mock entry object for the RSS parser
                        class MockEntry:
                            def __init__(self, raw_article):
                                self.link = raw_article.get('url', '')
                                self.title = raw_article.get('title', '')
                                self.content = [type('Content', (), {'value': raw_article.get('content', '')})] if raw_article.get('content') else []
                                self.summary = raw_article.get('content', '')
                                self.description = raw_article.get('content', '')
                                self.author = raw_article.get('author', '')
                                self.tags = raw_article.get('tags', [])
                                self.published = raw_article.get('publication_date', '').isoformat() if raw_article.get('publication_date') else None
                                self.updated = raw_article.get('publication_date', '').isoformat() if raw_article.get('publication_date') else None

                        mock_entry = MockEntry(matching_article)

                        # Extract the correct article URL using our new logic
                        extracted_url = parser._extract_article_url(mock_entry, article.origin)

                        if extracted_url and extracted_url != article.url:
                            # Update the article with the correct URL
                            logger.info(f"Updating Reddit article URL: {article.url} -> {extracted_url}")

                            # Update the article in the database
                            loop.run_until_complete(
                                article_repository.update_article_url(article.url, extracted_url)
                            )
                            updated_count += 1

                            logger.debug(f"✅ Updated article: {article.title}")
                        else:
                            logger.debug(f"⏭️ No URL change needed for: {article.title}")
                    else:
                        logger.warning(f"Could not find matching article in RSS feed: {article.title}")

                except Exception as e:
                    error_msg = f"Error processing article {article.url}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            logger.info(f"✅ Reddit backfill completed: {updated_count}/{len(articles)} articles updated")

            return {
                'success': True,
                'articles_processed': len(articles),
                'articles_updated': updated_count,
                'errors': errors[:10],  # Limit errors to first 10
                'error_count': len(errors),
                'timestamp': datetime.utcnow().isoformat()
            }

        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"💥 Reddit backfill task failed: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'timestamp': datetime.utcnow().isoformat()
        }


@celery_app.task(bind=True, base=CallbackTask, name='celery_app.tasks.reddit_backfill_stats_task')
def reddit_backfill_stats_task(self) -> Dict[str, Any]:
    """
    Get statistics about Reddit articles for backfill planning.

    Returns:
        Dictionary with Reddit article statistics
    """
    try:
        logger.info("📊 Getting Reddit backfill statistics")

        # Run the async operations in sync context
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # Ensure database connection
            loop.run_until_complete(ensure_database_connection())

            # Get total count of Reddit articles
            total_count = loop.run_until_complete(
                article_repository.count_reddit_articles()
            )

            # Get a sample of Reddit articles to analyze
            sample_articles = loop.run_until_complete(
                article_repository.get_reddit_articles(limit=100)
            )

            # Analyze URL patterns
            reddit_urls = 0
            external_urls = 0

            for article in sample_articles:
                if 'reddit.com' in str(article.url).lower():
                    reddit_urls += 1
                else:
                    external_urls += 1

            logger.info(f"📈 Reddit backfill stats: {total_count} total articles, {reddit_urls} Reddit URLs, {external_urls} external URLs in sample")

            return {
                'success': True,
                'total_reddit_articles': total_count,
                'sample_size': len(sample_articles),
                'reddit_urls_in_sample': reddit_urls,
                'external_urls_in_sample': external_urls,
                'estimated_updates_needed': reddit_urls,  # Rough estimate
                'timestamp': datetime.utcnow().isoformat()
            }

        finally:
            loop.close()

    except Exception as exc:
        logger.error(f"💥 Reddit backfill stats task failed: {exc}")
        return {
            'success': False,
            'error': str(exc),
            'timestamp': datetime.utcnow().isoformat()
        }

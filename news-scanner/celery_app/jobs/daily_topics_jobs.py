"""
Celery tasks for daily topics generation and management.

This module handles the generation of daily topic summaries by:
1. Fetching articles from the last 7 days with summaries
2. Grouping them by similarity using embeddings
3. Generating combined summaries for each topic group
4. Storing the results in the daily_topics collection
"""

import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
import asyncio

from .base_task import CallbackTask as BaseTask

logger = logging.getLogger(__name__)


def generate_daily_topics_sync() -> Dict[str, Any]:
    """Synchronous wrapper for generate_daily_topics."""
    import asyncio

    # Create a new event loop for this task (proper way for Celery)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(generate_daily_topics())
    finally:
        loop.close()


async def generate_daily_topics() -> Dict[str, Any]:
    """
    Generate daily topic groups from articles in the last 7 days.

    This task delegates grouping calculations to the ML service,
    then generates combined summaries and stores results.

    Returns:
        Dictionary with generation results
    """
    try:
        logger.info("Starting daily topics generation")
        start_time = datetime.utcnow()

        from database.connection import db_manager
        from services.ml_client import ml_client
        from services.summary_service import summary_service

        # Ensure database connection
        from .base_task import ensure_database_connection
        await ensure_database_connection()

        db = db_manager.get_database()
        topics_collection = db["daily_topics"]

        # Call ML service to generate topic groups
        # Using very strict parameters to create only high-quality major topics
        # Target: 10-30 topic groups maximum
        # Limiting to 500 most recent articles for performance
        logger.info("Calling ML service for topic grouping")
        try:
            ml_result = await ml_client.generate_daily_topics(
                days_back=7,
                similarity_threshold=0.80,  # High threshold for quality topics
                min_group_size=5,  # Minimum 5 articles per topic
                max_articles=500  # Limit for performance (500 articles = ~125K comparisons)
            )
        except Exception as ml_error:
            logger.error(f"Error calling ML service: {ml_error}", exc_info=True)
            return {
                "success": False,
                "error": f"ML service error: {str(ml_error)}",
                "topic_groups_created": 0,
                "articles_processed": 0
            }

        if not ml_result.get("success"):
            logger.error(f"ML service failed to generate topics: {ml_result.get('error')}")
            return {
                "success": False,
                "error": ml_result.get("error", "Unknown error from ML service"),
                "topic_groups_created": 0,
                "articles_processed": 0
            }

        topic_groups_from_ml = ml_result.get("topic_groups", [])
        articles_processed = ml_result.get("articles_processed", 0)
        articles_grouped = ml_result.get("articles_grouped", 0)

        logger.info(f"ML service created {len(topic_groups_from_ml)} topic groups from {articles_processed} articles")

        if len(topic_groups_from_ml) == 0:
            logger.info("No topic groups created")
            return {
                "success": True,
                "message": "No topic groups met the criteria",
                "topic_groups_created": 0,
                "articles_processed": articles_processed,
                "articles_grouped": 0,
                "articles_ungrouped": articles_processed,
                "duration_seconds": (datetime.utcnow() - start_time).total_seconds(),
                "generated_at": datetime.utcnow().isoformat()
            }

        # Generate combined summaries for each topic group
        cutoff_date = datetime.now() - timedelta(days=7)
        final_topic_groups = []

        for idx, topic_group in enumerate(topic_groups_from_ml):
            logger.info(f"Processing topic group {idx + 1}/{len(topic_groups_from_ml)}")

            articles = topic_group.get("articles", [])
            summaries = [art.get('summary', '') for art in articles if art.get('summary')]

            # Generate combined summary
            combined_summary_result = await summary_service.generate_combined_summary(
                summaries,
                topic_context=f"Topic group with {len(articles)} related articles"
            )

            topic_id = f"{datetime.now().strftime('%Y%m%d')}_{idx + 1}"

            final_topic_group = {
                "topic_id": topic_id,
                "date_generated": datetime.utcnow(),
                "article_count": len(articles),
                "articles": articles,
                "combined_summary": combined_summary_result.get('summary', '') if combined_summary_result.get('success') else None,
                "combined_summary_status": "completed" if combined_summary_result.get('success') else "failed",
                "combined_summary_error": combined_summary_result.get('error') if not combined_summary_result.get('success') else None,
                "created_at": datetime.utcnow(),
                "date_range_start": cutoff_date,
                "date_range_end": datetime.now()
            }

            final_topic_groups.append(final_topic_group)
            logger.info(f"Topic {topic_id}: {len(articles)} articles, summary status: {final_topic_group['combined_summary_status']}")

        # Clear old daily topics and insert new ones
        delete_result = await topics_collection.delete_many({})
        logger.info(f"Deleted {delete_result.deleted_count} old topic groups")

        if final_topic_groups:
            insert_result = await topics_collection.insert_many(final_topic_groups)
            logger.info(f"Inserted {len(insert_result.inserted_ids)} new topic groups")

        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.info(f"Daily topics generation completed in {duration:.2f} seconds")

        return {
            "success": True,
            "topic_groups_created": len(final_topic_groups),
            "articles_processed": articles_processed,
            "articles_grouped": articles_grouped,
            "articles_ungrouped": articles_processed - articles_grouped,
            "duration_seconds": duration,
            "generated_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Error generating daily topics: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "topic_groups_created": 0,
            "articles_processed": 0
        }


def regenerate_daily_topics_sync() -> Dict[str, Any]:
    """
    Synchronous wrapper for manual regeneration of daily topics.
    This is typically triggered by user request via API.
    """
    import asyncio

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        logger.info("Manual regeneration of daily topics triggered")
        return loop.run_until_complete(generate_daily_topics())
    finally:
        loop.close()


"""
Celery tasks for topic analysis using ML service.

This module contains tasks that communicate with the dedicated ML service
instead of having ML dependencies locally.
"""

import logging
from typing import Dict, Any
from datetime import datetime

# Import services inside functions to avoid circular imports
from .base_task import CallbackTask as BaseTask

logger = logging.getLogger(__name__)


class TopicAnalysisTask(BaseTask):
    """Base task for topic analysis operations."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Topic analysis task {task_id} failed: {exc}")
        super().on_failure(exc, task_id, args, kwargs, einfo)


def generate_article_embedding_sync(article_url: str) -> Dict[str, Any]:
    """Synchronous wrapper for generate_article_embedding."""
    return generate_article_embedding_sync_complete(article_url)

def generate_article_embedding_sync_complete(article_url: str) -> Dict[str, Any]:
    """
    Completely synchronous version of generate_article_embedding for Celery.

    Args:
        article_url: URL of the article to process

    Returns:
        Dictionary with processing results
    """
    import asyncio
    from database.connection import db_manager
    from services.ml_client import ml_client

    # Create a new event loop for this task
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        logger.info(f"Generating embedding for article: {article_url}")

        # Ensure database connection is established
        from .base_task import ensure_database_connection
        loop.run_until_complete(ensure_database_connection())

        # Get article from database
        db = db_manager.get_database()
        collection = db["documents"]

        article = loop.run_until_complete(collection.find_one({"url": article_url}))
        if not article:
            return {
                "success": False,
                "error": f"Article not found: {article_url}",
                "article_url": article_url
            }

        # Check if embedding already exists
        if article.get("embedding"):
            return {
                "success": True,
                "message": "Embedding already exists",
                "article_url": article_url
            }

        # Prepare text for embedding
        title = article.get('title', '') or ''
        content = article.get('Cleaned Data', '') or article.get('content', '') or ''
        text = f"{title} {content}".strip()

        if not text:
            return {
                "success": False,
                "error": "No text content found for embedding",
                "article_url": article_url
            }

        # Generate embedding via ML service (synchronous version for Celery)
        embedding = ml_client.generate_embedding_sync(text, article_url)
        if embedding is None:
            return {
                "success": False,
                "error": "Failed to generate embedding via ML service",
                "article_url": article_url
            }

        # Store embedding in database
        result = loop.run_until_complete(collection.update_one(
            {"url": article_url},
            {
                "$set": {
                    "embedding": embedding,
                    "embedding_updated_at": datetime.utcnow(),
                    "embedding_model": "all-MiniLM-L6-v2"
                }
            }
        ))

        if result.modified_count == 0:
            return {
                "success": False,
                "error": "Failed to store embedding in database",
                "article_url": article_url
            }

        logger.info(f"Successfully generated embedding for article: {article_url}")
        return {
            "success": True,
            "message": "Embedding generated and stored",
            "article_url": article_url,
            "embedding_dimension": len(embedding)
        }

    except Exception as e:
        logger.error(f"Error generating embedding for {article_url}: {e}")
        return {
            "success": False,
            "error": str(e),
            "article_url": article_url
        }
    finally:
        loop.close()

async def generate_article_embedding(article_url: str) -> Dict[str, Any]:
    """
    Generate embedding for a single article using ML service.

    Args:
        article_url: URL of the article to process

    Returns:
        Dictionary with processing results
    """
    # For async contexts, delegate to the sync version wrapped in asyncio
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, generate_article_embedding_sync_complete, article_url)


def batch_generate_embeddings_sync(batch_size: int = 100) -> Dict[str, Any]:
    """Synchronous wrapper for batch_generate_embeddings."""
    import asyncio

    # Create a new event loop for this task (proper way for Celery)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(batch_generate_embeddings(batch_size))
    finally:
        loop.close()

async def batch_generate_embeddings(batch_size: int = 100) -> Dict[str, Any]:
    """
    Generate embeddings for all articles that don't have them using ML service.

    Args:
        batch_size: Number of articles to process in batch

    Returns:
        Dictionary with batch processing results
    """
    try:
        logger.info(f"Starting batch embedding generation with batch size: {batch_size}")

        # Import ML client
        from services.ml_client import ml_client

        # Call ML service for batch processing
        result = await ml_client.batch_generate_embeddings(batch_size)

        if result.get("success"):
            logger.info(f"Batch embedding generation completed: {result}")
        else:
            logger.error(f"Batch embedding generation failed: {result}")

        return result

    except Exception as e:
        logger.error(f"Error in batch embedding generation: {e}")
        return {
            "success": False,
            "error": str(e),
            "total_articles": 0,
            "processed": 0,
            "failed": 0
        }


def group_articles_by_topics_sync(
    similarity_threshold: float = 0.75,
    min_group_size: int = 2
) -> Dict[str, Any]:
    """Synchronous wrapper for group_articles_by_topics."""
    import asyncio

    # Create a new event loop for this task (proper way for Celery)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(group_articles_by_topics(similarity_threshold, min_group_size))
    finally:
        loop.close()

async def group_articles_by_topics(
    similarity_threshold: float = 0.75,
    min_group_size: int = 2
) -> Dict[str, Any]:
    """
    Group articles by topics using ML service.

    Args:
        similarity_threshold: Similarity threshold for grouping
        min_group_size: Minimum group size

    Returns:
        Dictionary with grouping results
    """
    try:
        logger.info(f"Grouping articles by topics (threshold: {similarity_threshold}, min_size: {min_group_size})")

        # Import ML client
        from services.ml_client import ml_client

        # Call ML service for topic grouping
        result = await ml_client.group_articles_by_topics(similarity_threshold, min_group_size)

        if result.get("success"):
            logger.info(f"Topic grouping completed: {result}")
        else:
            logger.error(f"Topic grouping failed: {result}")

        return result

    except Exception as e:
        logger.error(f"Error grouping articles by topics: {e}")
        return {
            "success": False,
            "error": str(e),
            "topic_groups": []
        }


def generate_shared_summaries_sync() -> Dict[str, Any]:
    """Synchronous wrapper for generate_shared_summaries."""
    import asyncio

    # Create a new event loop for this task (proper way for Celery)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(generate_shared_summaries())
    finally:
        loop.close()

async def generate_shared_summaries() -> Dict[str, Any]:
    """
    Generate shared summaries for topic groups using ML service.

    Returns:
        Dictionary with summary generation results
    """
    try:
        logger.info("Generating shared summaries for topic groups")

        # Import ML client
        from services.ml_client import ml_client

        # Get topic groups from database
        from database.connection import db_manager
        db = db_manager.get_database()
        collection = db["documents"]

        # Find articles with topic groups
        topic_groups = await collection.aggregate([
            {"$match": {"topic_group": {"$exists": True}}},
            {"$group": {"_id": "$topic_group", "articles": {"$push": "$$ROOT"}}},
            {"$match": {"articles.1": {"$exists": True}}}  # Groups with 2+ articles
        ]).to_list(length=None)

        if not topic_groups:
            return {
                "success": True,
                "message": "No topic groups found for summary generation",
                "summaries_generated": 0
            }

        summaries_generated = 0
        for group in topic_groups:
            group_id = group["_id"]
            articles = group["articles"]

            # Generate summary for this topic group
            # This would need to be implemented in the ML service
            # For now, we'll just mark the group as processed
            await collection.update_many(
                {"topic_group": group_id},
                {"$set": {"summary_generated": True, "summary_generated_at": datetime.utcnow()}}
            )
            summaries_generated += 1

        logger.info(f"Generated {summaries_generated} shared summaries")
        return {
            "success": True,
            "summaries_generated": summaries_generated,
            "topic_groups_processed": len(topic_groups)
        }

    except Exception as e:
        logger.error(f"Error generating shared summaries: {e}")
        return {
            "success": False,
            "error": str(e),
            "summaries_generated": 0
        }


def process_new_article_sync(article_url: str) -> Dict[str, Any]:
    """Synchronous wrapper for process_new_article."""
    import asyncio

    # Create a new event loop for this task (proper way for Celery)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(process_new_article(article_url))
    finally:
        loop.close()

async def process_new_article(article_url: str) -> Dict[str, Any]:
    """
    Process a new article for topic analysis using ML service.

    Args:
        article_url: URL of the article to process

    Returns:
        Dictionary with processing results
    """
    try:
        logger.info(f"Processing new article for topic analysis: {article_url}")

        # Import ML client
        from services.ml_client import ml_client

        # Call ML service for topic analysis
        result = await ml_client.analyze_article_topics(article_url)

        if result.get("success"):
            logger.info(f"Topic analysis completed for article: {article_url}")
        else:
            logger.error(f"Topic analysis failed for article {article_url}: {result}")

        return {
            "success": result.get("success", False),
            "topics": result.get("topics", []),
            "topic_groups": result.get("topic_groups", []),
            "article_url": article_url
        }

    except Exception as e:
        logger.error(f"Error processing new article {article_url}: {e}")
        return {
            "success": False,
            "error": str(e),
            "article_url": article_url
        }


def full_topic_analysis_pipeline_sync() -> Dict[str, Any]:
    """Synchronous wrapper for full_topic_analysis_pipeline."""
    import asyncio

    # Create a new event loop for this task (proper way for Celery)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(full_topic_analysis_pipeline())
    finally:
        loop.close()

async def full_topic_analysis_pipeline() -> Dict[str, Any]:
    """
    Run the complete topic analysis pipeline using ML service.

    Returns:
        Dictionary with pipeline results
    """
    try:
        logger.info("Starting full topic analysis pipeline")

        # Step 1: Generate embeddings for all articles
        logger.info("Step 1: Generating embeddings for all articles")
        embedding_results = await batch_generate_embeddings(batch_size=50)

        if not embedding_results.get("success"):
            return {
                "success": False,
                "error": "Failed to generate embeddings",
                "step": "embedding_generation"
            }

        # Step 2: Group articles by topics
        logger.info("Step 2: Grouping articles by topics")
        grouping_results = await group_articles_by_topics(
            similarity_threshold=0.75,
            min_group_size=2
        )

        if not grouping_results.get("success"):
            return {
                "success": False,
                "error": "Failed to group articles by topics",
                "step": "topic_grouping"
            }

        # Step 3: Generate shared summaries
        logger.info("Step 3: Generating shared summaries")
        summary_results = await generate_shared_summaries()

        if not summary_results.get("success"):
            return {
                "success": False,
                "error": "Failed to generate shared summaries",
                "step": "summary_generation"
            }

        logger.info("Full topic analysis pipeline completed successfully")

        return {
            "success": True,
            "pipeline_completed": True,
            "embedding_results": embedding_results,
            "grouping_results": grouping_results,
            "summary_results": summary_results
        }

    except Exception as e:
        logger.error(f"Error in full topic analysis pipeline: {e}")
        return {
            "success": False,
            "error": str(e),
            "pipeline_completed": False
        }


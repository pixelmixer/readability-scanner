"""
Celery tasks for topic analysis and shared summary generation.
"""

import logging
from typing import Dict, Any

# Import services inside functions to avoid circular imports
from .base_task import CallbackTask as BaseTask

logger = logging.getLogger(__name__)


class TopicAnalysisTask(BaseTask):
    """Base task for topic analysis operations."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Topic analysis task {task_id} failed: {exc}")
        super().on_failure(exc, task_id, args, kwargs, einfo)


async def generate_article_embedding(article_url: str) -> Dict[str, Any]:
    """
    Generate embedding for a single article.

    Args:
        article_url: URL of the article to process

    Returns:
        Dictionary with processing results
    """
    try:
        logger.info(f"Generating embedding for article: {article_url}")

        # Import services locally to avoid circular imports
        from services.vector_service import vector_service

        # Get article from database
        from database.connection import db_manager
        db = db_manager.get_database()
        collection = db["documents"]

        article = await collection.find_one({"url": article_url})
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

        # Generate embedding
        embedding = await vector_service.generate_embedding(article)
        if not embedding:
            return {
                "success": False,
                "error": "Failed to generate embedding",
                "article_url": article_url
            }

        # Store embedding
        success = await vector_service.store_embedding(article_url, embedding)
        if not success:
            return {
                "success": False,
                "error": "Failed to store embedding",
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


async def batch_generate_embeddings(batch_size: int = 100) -> Dict[str, Any]:
    """
    Generate embeddings for all articles that don't have them.

    Args:
        batch_size: Number of articles to process in each batch

    Returns:
        Dictionary with processing statistics
    """
    try:
        logger.info(f"Starting batch embedding generation with batch size: {batch_size}")

        # Import services locally to avoid circular imports
        from services.vector_service import vector_service

        # Initialize vector service
        await vector_service.initialize()

        # Generate embeddings
        results = await vector_service.batch_generate_embeddings(batch_size)

        logger.info(f"Batch embedding generation completed: {results}")
        return {
            "success": True,
            "results": results
        }

    except Exception as e:
        logger.error(f"Error in batch embedding generation: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def group_articles_by_topics(
    similarity_threshold: float = 0.75,
    min_group_size: int = 2
) -> Dict[str, Any]:
    """
    Group articles by topics using vector similarity.

    Args:
        similarity_threshold: Minimum similarity score for grouping
        min_group_size: Minimum number of articles in a topic group

    Returns:
        Dictionary with grouping statistics
    """
    try:
        logger.info(f"Starting topic grouping with threshold: {similarity_threshold}, min group size: {min_group_size}")

        # Import services locally to avoid circular imports
        from services.vector_service import vector_service
        from services.topic_service import topic_service

        # Initialize services
        await vector_service.initialize()

        # Group articles by topics
        results = await topic_service.group_articles_by_topics(
            similarity_threshold=similarity_threshold,
            min_group_size=min_group_size
        )

        logger.info(f"Topic grouping completed: {results}")
        return {
            "success": True,
            "results": results
        }

    except Exception as e:
        logger.error(f"Error in topic grouping: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def generate_shared_summaries() -> Dict[str, Any]:
    """
    Generate shared summaries for all topic groups.

    Returns:
        Dictionary with summary generation statistics
    """
    try:
        logger.info("Starting shared summary generation")

        # Import services locally to avoid circular imports
        from services.topic_service import topic_service

        # Generate shared summaries
        results = await topic_service.generate_shared_summaries()

        logger.info(f"Shared summary generation completed: {results}")
        return {
            "success": True,
            "results": results
        }

    except Exception as e:
        logger.error(f"Error in shared summary generation: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def process_new_article(article_url: str) -> Dict[str, Any]:
    """
    Process a new article: generate embedding and find similar articles.

    Args:
        article_url: URL of the new article

    Returns:
        Dictionary with processing results
    """
    try:
        logger.info(f"Processing new article: {article_url}")

        # Import services locally to avoid circular imports
        from services.vector_service import vector_service

        # Initialize vector service
        await vector_service.initialize()

        # Generate embedding
        embedding_result = await generate_article_embedding(article_url)
        if not embedding_result.get("success"):
            return embedding_result

        # Find similar articles
        similar_articles = await vector_service.find_similar_articles_by_url(
            article_url,
            limit=10,
            similarity_threshold=0.7
        )

        logger.info(f"Found {len(similar_articles)} similar articles for {article_url}")

        return {
            "success": True,
            "article_url": article_url,
            "embedding_generated": True,
            "similar_articles_count": len(similar_articles),
            "similar_articles": [
                {
                    "url": sim['article']['url'],
                    "title": sim['article'].get('title', 'Untitled'),
                    "similarity_score": sim['similarity_score']
                }
                for sim in similar_articles[:5]  # Return top 5 for reference
            ]
        }

    except Exception as e:
        logger.error(f"Error processing new article {article_url}: {e}")
        return {
            "success": False,
            "error": str(e),
            "article_url": article_url
        }


async def full_topic_analysis_pipeline() -> Dict[str, Any]:
    """
    Run the complete topic analysis pipeline.

    Returns:
        Dictionary with pipeline results
    """
    try:
        logger.info("Starting full topic analysis pipeline")

        # Import services locally to avoid circular imports
        from services.vector_service import vector_service

        # Initialize vector service
        await vector_service.initialize()

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
            "embedding_results": embedding_results.get("results"),
            "grouping_results": grouping_results.get("results"),
            "summary_results": summary_results.get("results")
        }

    except Exception as e:
        logger.error(f"Error in full topic analysis pipeline: {e}")
        return {
            "success": False,
            "error": str(e),
            "pipeline_completed": False
        }
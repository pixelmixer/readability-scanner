#!/usr/bin/env python3
"""
Topic analysis setup and management script.

This script helps with initial setup and management of the topic analysis system.
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.connection import connect_to_database, close_database_connection
from services.vector_service import vector_service
from services.topic_service import topic_service
from celery_app.tasks import (
    batch_generate_embeddings,
    group_articles_by_topics,
    generate_shared_summaries,
    full_topic_analysis_pipeline
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TopicAnalysisManager:
    """Manager for topic analysis operations."""

    def __init__(self):
        self.initialized = False

    async def initialize(self):
        """Initialize the topic analysis system."""
        try:
            logger.info("Initializing topic analysis system...")

            # Connect to database
            await connect_to_database()

            # Initialize vector service
            await vector_service.initialize()

            self.initialized = True
            logger.info("Topic analysis system initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize topic analysis system: {e}")
            raise

    async def cleanup(self):
        """Cleanup resources."""
        try:
            await close_database_connection()
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")

    async def run_full_pipeline(self):
        """Run the complete topic analysis pipeline."""
        if not self.initialized:
            await self.initialize()

        try:
            logger.info("Starting full topic analysis pipeline...")

            # Run the pipeline as a Celery task
            result = await full_topic_analysis_pipeline()

            if result.get("success"):
                logger.info("Full topic analysis pipeline completed successfully")
                logger.info(f"Results: {result}")
            else:
                logger.error(f"Pipeline failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Error running full pipeline: {e}")

    async def generate_embeddings_only(self, batch_size: int = 100):
        """Generate embeddings for all articles."""
        if not self.initialized:
            await self.initialize()

        try:
            logger.info(f"Generating embeddings with batch size: {batch_size}")

            result = await batch_generate_embeddings(batch_size)

            if result.get("success"):
                logger.info("Embedding generation completed successfully")
                logger.info(f"Results: {result.get('results')}")
            else:
                logger.error(f"Embedding generation failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")

    async def group_topics_only(self, similarity_threshold: float = 0.75, min_group_size: int = 2):
        """Group articles by topics only."""
        if not self.initialized:
            await self.initialize()

        try:
            logger.info(f"Grouping articles by topics (threshold: {similarity_threshold}, min group size: {min_group_size})")

            result = await group_articles_by_topics(similarity_threshold, min_group_size)

            if result.get("success"):
                logger.info("Topic grouping completed successfully")
                logger.info(f"Results: {result.get('results')}")
            else:
                logger.error(f"Topic grouping failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Error grouping topics: {e}")

    async def generate_summaries_only(self):
        """Generate shared summaries only."""
        if not self.initialized:
            await self.initialize()

        try:
            logger.info("Generating shared summaries...")

            result = await generate_shared_summaries()

            if result.get("success"):
                logger.info("Summary generation completed successfully")
                logger.info(f"Results: {result.get('results')}")
            else:
                logger.error(f"Summary generation failed: {result.get('error')}")

        except Exception as e:
            logger.error(f"Error generating summaries: {e}")

    async def get_stats(self):
        """Get topic analysis statistics."""
        if not self.initialized:
            await self.initialize()

        try:
            from database.connection import db_manager

            db = db_manager.get_database()

            # Get article statistics
            collection = db["documents"]
            total_articles = await collection.count_documents({})
            articles_with_embeddings = await collection.count_documents({"embedding": {"$exists": True}})

            # Get topic group statistics
            topics_collection = db["article_topics"]
            total_topic_groups = await topics_collection.count_documents({})
            topic_groups_with_summaries = await topics_collection.count_documents({"shared_summary": {"$exists": True}})

            stats = {
                "articles": {
                    "total": total_articles,
                    "with_embeddings": articles_with_embeddings,
                    "embedding_coverage": (articles_with_embeddings / total_articles * 100) if total_articles > 0 else 0
                },
                "topic_groups": {
                    "total": total_topic_groups,
                    "with_summaries": topic_groups_with_summaries,
                    "summary_coverage": (topic_groups_with_summaries / total_topic_groups * 100) if total_topic_groups > 0 else 0
                }
            }

            logger.info("Topic analysis statistics:")
            logger.info(f"  Total articles: {stats['articles']['total']}")
            logger.info(f"  Articles with embeddings: {stats['articles']['with_embeddings']} ({stats['articles']['embedding_coverage']:.1f}%)")
            logger.info(f"  Topic groups: {stats['topic_groups']['total']}")
            logger.info(f"  Topic groups with summaries: {stats['topic_groups']['with_summaries']} ({stats['topic_groups']['summary_coverage']:.1f}%)")

            return stats

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return None


async def main():
    """Main function for command-line usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Topic Analysis Management Script")
    parser.add_argument("command", choices=[
        "full-pipeline", "embeddings", "group-topics", "summaries", "stats"
    ], help="Command to run")
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size for embedding generation")
    parser.add_argument("--similarity-threshold", type=float, default=0.75, help="Similarity threshold for topic grouping")
    parser.add_argument("--min-group-size", type=int, default=2, help="Minimum group size for topic grouping")

    args = parser.parse_args()

    manager = TopicAnalysisManager()

    try:
        if args.command == "full-pipeline":
            await manager.run_full_pipeline()
        elif args.command == "embeddings":
            await manager.generate_embeddings_only(args.batch_size)
        elif args.command == "group-topics":
            await manager.group_topics_only(args.similarity_threshold, args.min_group_size)
        elif args.command == "summaries":
            await manager.generate_summaries_only()
        elif args.command == "stats":
            await manager.get_stats()

    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        sys.exit(1)
    finally:
        await manager.cleanup()


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Test script for the topic analysis system.
"""

import asyncio
import logging
import sys
import os

# Add the current directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.connection import connect_to_database, close_database_connection
from services.vector_service import vector_service
from services.topic_service import topic_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_vector_service():
    """Test the vector service functionality."""
    logger.info("Testing vector service...")

    try:
        # Initialize vector service
        await vector_service.initialize()
        logger.info("✓ Vector service initialized successfully")

        # Test with a sample article
        sample_article = {
            "url": "https://example.com/test-article",
            "title": "Test Article About Technology",
            "content": "This is a test article about artificial intelligence and machine learning technologies.",
            "Cleaned Data": "This is a test article about artificial intelligence and machine learning technologies."
        }

        # Generate embedding
        embedding = await vector_service.generate_embedding(sample_article)
        if embedding:
            logger.info(f"✓ Generated embedding with {len(embedding)} dimensions")
        else:
            logger.error("✗ Failed to generate embedding")
            return False

        # Store embedding
        success = await vector_service.store_embedding(sample_article["url"], embedding)
        if success:
            logger.info("✓ Stored embedding successfully")
        else:
            logger.error("✗ Failed to store embedding")
            return False

        return True

    except Exception as e:
        logger.error(f"✗ Vector service test failed: {e}")
        return False


async def test_topic_service():
    """Test the topic service functionality."""
    logger.info("Testing topic service...")

    try:
        # Test getting similar articles (this will work even with minimal data)
        similar_articles = await topic_service.get_similar_articles_for_display(
            "https://example.com/test-article",
            limit=5
        )
        logger.info(f"✓ Found {len(similar_articles)} similar articles")

        # Test getting article topics
        topics = await topic_service.get_article_topics("https://example.com/test-article")
        logger.info(f"✓ Found {len(topics)} topic groups")

        return True

    except Exception as e:
        logger.error(f"✗ Topic service test failed: {e}")
        return False


async def test_database_connection():
    """Test database connection."""
    logger.info("Testing database connection...")

    try:
        await connect_to_database()
        logger.info("✓ Database connection successful")

        # Test basic query
        from database.connection import db_manager
        db = db_manager.get_database()
        collection = db["documents"]
        count = await collection.count_documents({})
        logger.info(f"✓ Found {count} articles in database")

        return True

    except Exception as e:
        logger.error(f"✗ Database connection test failed: {e}")
        return False


async def main():
    """Run all tests."""
    logger.info("Starting topic analysis system tests...")

    tests = [
        ("Database Connection", test_database_connection),
        ("Vector Service", test_vector_service),
        ("Topic Service", test_topic_service),
    ]

    results = []

    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} Test ---")
        try:
            result = await test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results.append((test_name, False))

    # Summary
    logger.info("\n" + "="*50)
    logger.info("TEST RESULTS SUMMARY")
    logger.info("="*50)

    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        logger.info(f"{test_name}: {status}")
        if result:
            passed += 1

    logger.info(f"\nOverall: {passed}/{len(results)} tests passed")

    if passed == len(results):
        logger.info("🎉 All tests passed! Topic analysis system is ready.")
    else:
        logger.error("❌ Some tests failed. Check the logs above for details.")

    # Cleanup
    await close_database_connection()


if __name__ == "__main__":
    asyncio.run(main())

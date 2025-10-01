#!/usr/bin/env python3
"""
Test script for the date field cleanup functionality.
This script can be run to test the cleanup task locally.
"""

import asyncio
import logging
from datetime import datetime
from database.articles import article_repository
from database.connection import db_manager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_date_field_cleanup():
    """Test the date field cleanup functionality."""
    try:
        logger.info("🧪 Testing date field cleanup functionality")

        # Connect to database
        await db_manager.connect()
        logger.info("✅ Connected to database")

        # Get the collection directly
        collection = article_repository.collection

        # Check current state
        total_docs = await collection.count_documents({})
        docs_with_old_field = await collection.count_documents({"publication date": {"$exists": True}})
        docs_with_new_field = await collection.count_documents({"publication_date": {"$exists": True}})
        docs_with_published_time = await collection.count_documents({"publishedTime": {"$exists": True}})

        logger.info(f"📊 Database state:")
        logger.info(f"  Total documents: {total_docs}")
        logger.info(f"  Documents with 'publication date': {docs_with_old_field}")
        logger.info(f"  Documents with 'publication_date': {docs_with_new_field}")
        logger.info(f"  Documents with 'publishedTime': {docs_with_published_time}")

        # Find a sample document with old fields
        sample_doc = await collection.find_one({"publication date": {"$exists": True}})
        if sample_doc:
            logger.info(f"📄 Sample document with old fields:")
            logger.info(f"  URL: {sample_doc.get('url', 'unknown')}")
            logger.info(f"  Has 'publication date': {'publication date' in sample_doc}")
            logger.info(f"  Has 'publication_date': {'publication_date' in sample_doc}")
            logger.info(f"  Has 'publishedTime': {'publishedTime' in sample_doc}")

        # Test the cleanup logic manually
        if docs_with_old_field > 0:
            logger.info("🧹 Testing cleanup logic on a single document...")

            # Get one document to test with
            test_doc = await collection.find_one({"publication date": {"$exists": True}})
            if test_doc:
                url = test_doc.get('url', 'unknown')
                old_pub_date = test_doc.get('publication date')
                new_pub_date = test_doc.get('publication_date')

                logger.info(f"📋 Test document: {url}")
                logger.info(f"  Old 'publication date': {old_pub_date}")
                logger.info(f"  New 'publication_date': {new_pub_date}")

                # Simulate the cleanup logic
                update_operations = {}
                fields_to_remove = []

                if old_pub_date and not new_pub_date:
                    update_operations['publication_date'] = old_pub_date
                    logger.info("  ✅ Would migrate 'publication date' to 'publication_date'")

                if 'publication date' in test_doc:
                    fields_to_remove.append('publication date')
                    logger.info("  ✅ Would remove 'publication date' field")

                if 'publishedTime' in test_doc:
                    fields_to_remove.append('publishedTime')
                    logger.info("  ✅ Would remove 'publishedTime' field")

                if update_operations or fields_to_remove:
                    logger.info(f"📝 Cleanup operations needed:")
                    logger.info(f"  Updates: {update_operations}")
                    logger.info(f"  Removals: {fields_to_remove}")
                else:
                    logger.info("ℹ️  No cleanup operations needed for this document")

        logger.info("✅ Test completed successfully")

    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        raise
    finally:
        await db_manager.disconnect()
        logger.info("🔌 Disconnected from database")


if __name__ == "__main__":
    asyncio.run(test_date_field_cleanup())

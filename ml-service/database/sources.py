"""
RSS source repository for MongoDB operations.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING
from bson import ObjectId

from models.source import Source, SourceCreate, SourceUpdate
from .connection import db_manager

logger = logging.getLogger(__name__)


class SourceRepository:
    """Repository for RSS source database operations."""

    def __init__(self):
        self.collection_name = "urls"  # Keep same collection name as Node.js version

    @property
    def collection(self) -> AsyncIOMotorCollection:
        """Get the sources collection."""
        return db_manager.get_collection(self.collection_name)

    async def create_indexes(self) -> None:
        """Create database indexes for optimal performance."""
        try:
            # Index on URL for uniqueness and fast lookups
            await self.collection.create_index("url", unique=True)

            # Index on name for searching
            await self.collection.create_index("name")

            # Index on date fields for sorting
            await self.collection.create_index("dateAdded")
            await self.collection.create_index("lastModified")
            await self.collection.create_index("lastRefreshed")

            logger.info("Source collection indexes created successfully")

        except Exception as e:
            logger.error(f"Error creating source indexes: {e}")

    async def create_source(self, source: SourceCreate) -> Optional[Source]:
        """Create a new RSS source."""
        try:
            # Prepare document
            doc = {
                "url": str(source.url),
                "name": source.name or urlparse(str(source.url)).hostname,
                "description": source.description or "",
                "dateAdded": datetime.now()
            }

            # Insert with upsert to handle duplicates
            result = await self.collection.replace_one(
                {"url": doc["url"]},
                doc,
                upsert=True
            )

            if result.upserted_id:
                logger.info(f"Created new source: {doc['url']}")
            else:
                logger.info(f"Updated existing source: {doc['url']}")

            # Return the created/updated source
            return await self.get_source_by_url(doc["url"])

        except Exception as e:
            logger.error(f"Error creating source: {e}")
            return None

    async def get_source_by_id(self, source_id: str) -> Optional[Source]:
        """Get a source by its ObjectId."""
        try:
            doc = await self.collection.find_one({"_id": ObjectId(source_id)})
            return Source.from_mongo(doc) if doc else None
        except Exception as e:
            logger.error(f"Error getting source by ID {source_id}: {e}")
            return None

    async def get_source_by_url(self, url: str) -> Optional[Source]:
        """Get a source by its URL."""
        try:
            doc = await self.collection.find_one({"url": url})
            return Source.from_mongo(doc) if doc else None
        except Exception as e:
            logger.error(f"Error getting source by URL {url}: {e}")
            return None

    async def get_all_sources(self) -> List[Source]:
        """Get all RSS sources."""
        try:
            cursor = self.collection.find({}).sort("_id", DESCENDING)
            docs = await cursor.to_list(length=None)
            return [Source.from_mongo(doc) for doc in docs]
        except Exception as e:
            logger.error(f"Error getting all sources: {e}")
            return []

    async def get_sources_with_stats(self) -> List[Dict[str, Any]]:
        """
        Get all sources with article count and latest article stats.

        This requires joining with the articles collection.
        """
        try:
            # Get basic sources
            sources = await self.get_all_sources()

            # Import here to avoid circular imports
            from .articles import article_repository

            enriched_sources = []
            for source in sources:
                # Convert URL to string for database queries (Pydantic v2 compatibility)
                source_url_str = str(source.url)

                # Get article count
                article_count = await article_repository.count_articles_by_origin(source_url_str)

                # Get latest article
                latest_article = await article_repository.get_latest_article_by_origin(source_url_str)

                # Convert to dict and add computed fields (Pydantic v2 compatibility)
                source_dict = source.model_dump(by_alias=True)  # Use aliases like _id

                # Convert URL to string for template compatibility
                source_dict["url"] = str(source.url)

                source_dict["article_count"] = article_count
                source_dict["last_fetched"] = latest_article.publication_date if latest_article else None

                enriched_sources.append(source_dict)

            return enriched_sources

        except Exception as e:
            logger.error(f"Error getting sources with stats: {e}")
            return []

    async def update_source(self, source_id: str, update_data: SourceUpdate) -> Optional[Source]:
        """Update an existing source."""
        try:
            # Prepare update document
            update_doc = {}
            if update_data.url is not None:
                update_doc["url"] = str(update_data.url)
            if update_data.name is not None:
                update_doc["name"] = update_data.name
            if update_data.description is not None:
                update_doc["description"] = update_data.description

            if update_doc:
                update_doc["lastModified"] = datetime.now()

                result = await self.collection.update_one(
                    {"_id": ObjectId(source_id)},
                    {"$set": update_doc}
                )

                if result.modified_count > 0:
                    logger.info(f"Updated source: {source_id}")
                    return await self.get_source_by_id(source_id)

            return None

        except Exception as e:
            logger.error(f"Error updating source {source_id}: {e}")
            return None

    async def delete_source(self, source_id: str) -> bool:
        """Delete a source."""
        try:
            result = await self.collection.delete_one({"_id": ObjectId(source_id)})
            if result.deleted_count > 0:
                logger.info(f"Deleted source: {source_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting source {source_id}: {e}")
            return False

    async def update_last_refreshed(self, source_id: str) -> bool:
        """Update the last refreshed timestamp for a source."""
        try:
            result = await self.collection.update_one(
                {"_id": ObjectId(source_id)},
                {"$set": {"lastRefreshed": datetime.now()}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error updating last refreshed for source {source_id}: {e}")
            return False

    async def get_source_urls(self) -> List[str]:
        """Get all source URLs for scanning."""
        try:
            cursor = self.collection.find({}, {"url": 1, "_id": 0})
            docs = await cursor.to_list(length=None)
            return [doc["url"] for doc in docs]
        except Exception as e:
            logger.error(f"Error getting source URLs: {e}")
            return []


# Global repository instance
source_repository = SourceRepository()

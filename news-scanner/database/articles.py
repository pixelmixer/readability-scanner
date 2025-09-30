"""
Article repository for MongoDB operations.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse

from motor.motor_asyncio import AsyncIOMotorCollection
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import DuplicateKeyError

from models.article import Article, ArticleCreate, ArticleUpdate
from .connection import db_manager

logger = logging.getLogger(__name__)


class ArticleRepository:
    """Repository for article database operations."""

    def __init__(self):
        self.collection_name = "documents"  # Keep same collection name as Node.js version

    def _clean_article_data(self, doc: dict) -> dict:
        """Clean article data for Pydantic v2 compatibility."""
        if doc is None:
            return doc

        # Handle Dale Chall Grade field that might be stored as list instead of string
        if "Dale Chall: Grade" in doc and isinstance(doc["Dale Chall: Grade"], list):
            # Convert list to string representation
            doc["Dale Chall: Grade"] = str(doc["Dale Chall: Grade"]).replace("[", "").replace("]", "")

        return doc

    @property
    def collection(self) -> AsyncIOMotorCollection:
        """Get the articles collection."""
        return db_manager.get_collection(self.collection_name)

    async def create_indexes(self) -> None:
        """Create database indexes for optimal performance."""
        try:
            # Index on URL for uniqueness and fast lookups
            await self.collection.create_index("url", unique=True)

            # Index on origin (RSS feed) for filtering by source
            await self.collection.create_index("origin")

            # Index on publication date for time-based queries
            await self.collection.create_index("publication date")

            # Index on host for hostname-based aggregations
            await self.collection.create_index("Host")

            # Compound index for common queries
            await self.collection.create_index([
                ("origin", ASCENDING),
                ("publication date", DESCENDING)
            ])

            logger.info("Article collection indexes created successfully")

        except Exception as e:
            logger.error(f"Error creating article indexes: {e}")

    async def upsert_article(self, article_data: Dict[str, Any]) -> bool:
        """
        Insert or update an article using upsert pattern.

        Args:
            article_data: Dictionary containing article data

        Returns:
            bool: True if successful
        """
        try:
            # Ensure required fields
            if "url" not in article_data:
                raise ValueError("Article data must contain 'url' field")

            # Add/update metadata
            article_data["date"] = datetime.now()

            # Extract hostname if not provided
            if "Host" not in article_data and "url" in article_data:
                parsed_url = urlparse(str(article_data["url"]))
                article_data["Host"] = parsed_url.hostname

            # Use upsert to replace existing or insert new
            result = await self.collection.replace_one(
                {"url": article_data["url"]},
                article_data,
                upsert=True
            )

            if result.upserted_id:
                logger.debug(f"Inserted new article: {article_data['url']}")
            else:
                logger.debug(f"Updated existing article: {article_data['url']}")

            return True

        except Exception as e:
            logger.error(f"Error upserting article {article_data.get('url', 'unknown')}: {e}")
            return False

    async def get_article_by_url(self, url: str) -> Optional[Article]:
        """Get an article by its URL."""
        try:
            doc = await self.collection.find_one({"url": url})
            if doc:
                doc = self._clean_article_data(doc)
                return Article(**doc)
            return None
        except Exception as e:
            logger.error(f"Error getting article by URL {url}: {e}")
            return None

    async def get_articles_by_origin(
        self,
        origin: str,
        limit: int = 100,
        skip: int = 0
    ) -> List[Article]:
        """Get articles from a specific RSS source."""
        try:
            cursor = self.collection.find({"origin": origin}).skip(skip).limit(limit)
            docs = await cursor.to_list(length=limit)
            return [Article(**doc) for doc in docs]
        except Exception as e:
            logger.error(f"Error getting articles by origin {origin}: {e}")
            return []

    async def count_articles_by_origin(self, origin: str) -> int:
        """Count articles from a specific RSS source."""
        try:
            return await self.collection.count_documents({"origin": origin})
        except Exception as e:
            logger.error(f"Error counting articles by origin {origin}: {e}")
            return 0

    async def get_latest_article_by_origin(self, origin: str) -> Optional[Article]:
        """Get the most recent article from a specific RSS source."""
        try:
            doc = await self.collection.find_one(
                {"origin": origin},
                sort=[("publication date", DESCENDING)]
            )
            if doc:
                doc = self._clean_article_data(doc)
                return Article(**doc)
            return None
        except Exception as e:
            logger.error(f"Error getting latest article by origin {origin}: {e}")
            return None

    async def get_articles_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        origin: Optional[str] = None
    ) -> List[Article]:
        """Get articles within a date range, optionally filtered by origin."""
        try:
            query = {
                "publication date": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }

            if origin:
                query["origin"] = origin

            cursor = self.collection.find(query).sort("publication date", DESCENDING)
            docs = await cursor.to_list(length=None)  # Get all matching documents
            return [Article(**doc) for doc in docs]

        except Exception as e:
            logger.error(f"Error getting articles by date range: {e}")
            return []

    async def aggregate_readability_by_host(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        min_articles: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Aggregate readability metrics by hostname.

        This matches the Node.js aggregation pipeline for compatibility.
        """
        try:
            pipeline = []

            # Match stage for date filtering
            match_stage = {
                "origin": {"$ne": None}
            }

            if start_date and end_date:
                match_stage["publication date"] = {
                    "$gte": start_date,
                    "$lte": end_date
                }

            pipeline.append({"$match": match_stage})

            # Group by Host and calculate averages
            group_stage = {
                "$group": {
                    "_id": "$Host",
                    "words": {"$avg": "$words"},
                    "sentences": {"$avg": "$sentences"},
                    "paragraphs": {"$avg": "$paragraphs"},
                    "characters": {"$avg": "$characters"},
                    "syllables": {"$avg": "$syllables"},
                    "word syllables": {"$avg": "$word syllables"},
                    "complex polysillabic words": {"$avg": "$complex polysillabic words"},
                    "Flesch": {"$avg": "$Flesch"},
                    "Flesch Kincaid": {"$avg": "$Flesch Kincaid"},
                    "Smog": {"$avg": "$Smog"},
                    "Dale Chall": {"$avg": "$Dale Chall"},
                    "Coleman Liau": {"$avg": "$Coleman Liau"},
                    "Gunning Fog": {"$avg": "$Gunning Fog"},
                    "Spache": {"$avg": "$Spache"},
                    "Automated Readability": {"$avg": "$Automated Readability"},
                    "origin": {"$first": "$origin"},
                    "articles": {"$sum": 1}
                }
            }
            pipeline.append(group_stage)

            # Filter by minimum article count
            pipeline.append({
                "$match": {
                    "_id": {"$ne": None},
                    "articles": {"$gte": min_articles}
                }
            })

            # Lookup source information
            pipeline.append({
                "$lookup": {
                    "from": "urls",
                    "localField": "origin",
                    "foreignField": "url",
                    "as": "host"
                }
            })

            # Merge source info
            pipeline.append({
                "$replaceRoot": {
                    "newRoot": {
                        "$mergeObjects": [
                            {"$arrayElemAt": ["$host", 0]},
                            "$$ROOT"
                        ]
                    }
                }
            })

            # Clean up
            pipeline.append({"$project": {"host": 0}})

            # Sort by Flesch score
            pipeline.append({"$sort": {"Flesch": -1}})

            cursor = self.collection.aggregate(pipeline)
            return await cursor.to_list(length=None)

        except Exception as e:
            logger.error(f"Error in readability aggregation: {e}")
            return []

    async def delete_articles_by_origin(self, origin: str) -> int:
        """Delete all articles from a specific origin. Returns count of deleted documents."""
        try:
            result = await self.collection.delete_many({"origin": origin})
            logger.info(f"Deleted {result.deleted_count} articles from origin: {origin}")
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error deleting articles by origin {origin}: {e}")
            return 0

    async def count_articles_before_date(self, cutoff_date: datetime) -> int:
        """Count articles published before a certain date."""
        try:
            count = await self.collection.count_documents({
                "publication date": {"$lt": cutoff_date}
            })
            return count
        except Exception as e:
            logger.error(f"Error counting old articles: {e}")
            return 0

    async def delete_articles_before_date(self, cutoff_date: datetime) -> int:
        """Delete articles published before a certain date."""
        try:
            result = await self.collection.delete_many({
                "publication date": {"$lt": cutoff_date}
            })
            logger.info(f"Deleted {result.deleted_count} articles older than {cutoff_date}")
            return result.deleted_count
        except Exception as e:
            logger.error(f"Error deleting old articles: {e}")
            return 0

    async def get_articles_without_summaries(self, limit: int = 100, skip: int = 0) -> List[Article]:
        """Get articles that don't have summaries yet."""
        try:
            query = {
                "$or": [
                    {"summary": {"$exists": False}},
                    {"summary": None},
                    {"summary": ""},
                    {"summary_processing_status": {"$in": ["pending", "failed"]}}
                ]
            }

            logger.debug(f"Querying articles without summaries: {query}")
            cursor = self.collection.find(query).skip(skip).limit(limit)
            docs = await cursor.to_list(length=limit)
            logger.debug(f"Found {len(docs)} raw documents from database")
            return [Article(**self._clean_article_data(doc)) for doc in docs]
        except Exception as e:
            logger.error(f"Error getting articles without summaries: {e}")
            return []

    async def count_articles_without_summaries(self) -> int:
        """Count articles that don't have summaries yet."""
        try:
            query = {
                "$or": [
                    {"summary": {"$exists": False}},
                    {"summary": None},
                    {"summary": ""},
                    {"summary_processing_status": {"$in": ["pending", "failed"]}}
                ]
            }
            count = await self.collection.count_documents(query)
            logger.debug(f"Count query result: {count} articles without summaries")
            return count
        except Exception as e:
            logger.error(f"Error counting articles without summaries: {e}")
            return 0

    async def update_article_summary(
        self,
        url: str,
        summary: str,
        model: str,
        prompt_version: str,
        status: str = "completed",
        error: str = None
    ) -> bool:
        """Update an article with summary information."""
        try:
            update_data = {
                "summary": summary,
                "summary_generated_at": datetime.utcnow(),
                "summary_model": model,
                "summary_prompt_version": prompt_version,
                "summary_processing_status": status
            }

            if error:
                update_data["summary_error"] = error
            else:
                # Clear any existing error by setting it to null
                update_data["summary_error"] = None

            result = await self.collection.update_one(
                {"url": url},
                {"$set": update_data}
            )

            if result.modified_count > 0:
                logger.debug(f"Updated summary for article: {url}")
                return True
            else:
                logger.warning(f"No article found with URL: {url}")
                return False

        except Exception as e:
            logger.error(f"Error updating article summary for {url}: {e}")
            return False

    async def get_summary_statistics(self) -> Dict[str, Any]:
        """Get statistics about summary processing."""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": "$summary_processing_status",
                        "count": {"$sum": 1}
                    }
                }
            ]

            cursor = self.collection.aggregate(pipeline)
            status_counts = await cursor.to_list(length=None)

            # Convert to dictionary
            stats = {}
            for item in status_counts:
                status = item["_id"] or "no_summary"
                stats[status] = item["count"]

            # Get total count
            total_articles = await self.collection.count_documents({})

            return {
                "total_articles": total_articles,
                "status_breakdown": stats,
                "summary_coverage": (stats.get("completed", 0) / total_articles * 100) if total_articles > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error getting summary statistics: {e}")
            return {"total_articles": 0, "status_breakdown": {}, "summary_coverage": 0}


# Global repository instance
article_repository = ArticleRepository()

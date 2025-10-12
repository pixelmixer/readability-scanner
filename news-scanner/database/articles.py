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
from utils.date_normalizer import normalize_date, ensure_utc_datetime

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

        # Note: We now use 'publication_date' consistently, no field mapping needed

        # Ensure publication_date is a proper datetime object for consistent sorting
        if "publication_date" in doc and doc["publication_date"] is not None:
            try:
                from datetime import datetime
                if isinstance(doc["publication_date"], str):
                    # Parse string date to datetime
                    from dateutil import parser
                    doc["publication_date"] = parser.parse(doc["publication_date"])
                elif hasattr(doc["publication_date"], 'to_pydatetime'):
                    # Convert MongoDB datetime to Python datetime
                    doc["publication_date"] = doc["publication_date"].to_pydatetime()
            except Exception as e:
                logger.warning(f"Error parsing publication_date {doc.get('publication_date')}: {e}")
                # Set to epoch if parsing fails
                doc["publication_date"] = datetime(1970, 1, 1)

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
            await self.collection.create_index("publication_date")

            # Index on host for hostname-based aggregations
            await self.collection.create_index("Host")

            # Compound index for common queries
            await self.collection.create_index([
                ("origin", ASCENDING),
                ("publication_date", DESCENDING)
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

            # Normalize and set dates
            current_time = ensure_utc_datetime(datetime.now())

            if "publication_date" not in article_data or article_data["publication_date"] is None:
                # No publication date, use current time
                article_data["publication_date"] = current_time
            else:
                # Normalize publication date to UTC
                normalized_pub_date = normalize_date(article_data["publication_date"])
                if normalized_pub_date:
                    article_data["publication_date"] = normalized_pub_date
                    article_data["analysis_date"] = current_time
                else:
                    # If normalization fails, use current time
                    logger.warning(f"Failed to normalize publication_date for {article_data.get('url')}, using current time")
                    article_data["publication_date"] = current_time

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

    async def upsert_article_with_status(self, article_data: Dict[str, Any]) -> tuple[bool, bool]:
        """
        Insert or update an article using upsert pattern and return creation status.

        Args:
            article_data: Dictionary containing article data

        Returns:
            tuple: (success: bool, was_new: bool) - success status and whether article was newly created
        """
        try:
            # Ensure required fields
            if "url" not in article_data:
                raise ValueError("Article data must contain 'url' field")

            # Normalize and set dates
            current_time = ensure_utc_datetime(datetime.now())

            if "publication_date" not in article_data or article_data["publication_date"] is None:
                # No publication date, use current time
                article_data["publication_date"] = current_time
            else:
                # Normalize publication date to UTC
                normalized_pub_date = normalize_date(article_data["publication_date"])
                if normalized_pub_date:
                    article_data["publication_date"] = normalized_pub_date
                    article_data["analysis_date"] = current_time
                else:
                    # If normalization fails, use current time
                    logger.warning(f"Failed to normalize publication_date for {article_data.get('url')}, using current time")
                    article_data["publication_date"] = current_time

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

            was_new = result.upserted_id is not None
            if was_new:
                logger.debug(f"Inserted new article: {article_data['url']}")
            else:
                logger.debug(f"Updated existing article: {article_data['url']}")

            return True, was_new

        except Exception as e:
            logger.error(f"Error upserting article {article_data.get('url', 'unknown')}: {e}")
            return False, False

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
                sort=[("publication_date", DESCENDING)]
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
                "publication_date": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }

            if origin:
                query["origin"] = origin

            cursor = self.collection.find(query).sort("publication_date", DESCENDING)
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
                match_stage["publication_date"] = {
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


    async def get_articles_without_summaries(self, limit: int = 100, skip: int = 0) -> List[Article]:
        """Get articles that don't have summaries yet, prioritized by publication date (newest first)."""
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
            # Sort by publication date (newest first), fallback to analysis date
            cursor = self.collection.find(query).sort([
                ("publication_date", -1),  # Newest publication dates first
                ("date", -1)              # Fallback to analysis date
            ]).skip(skip).limit(limit)
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

    async def get_articles_with_summaries_without_embeddings(self, limit: int = 50, skip: int = 0) -> List[Article]:
        """Get articles that have summaries but don't have summary embeddings yet."""
        try:
            query = {
                "summary": {"$exists": True, "$ne": None, "$ne": ""},
                "summary_processing_status": "completed",
                "summary_embedding": {"$exists": False}
            }

            logger.debug(f"Querying articles with summaries but without embeddings: {query}")
            # Sort by summary generation date (newest first)
            cursor = self.collection.find(query).sort([
                ("summary_generated_at", -1),
                ("publication_date", -1)
            ]).skip(skip).limit(limit)
            docs = await cursor.to_list(length=limit)
            logger.debug(f"Found {len(docs)} articles with summaries but without embeddings")
            return [Article(**self._clean_article_data(doc)) for doc in docs]
        except Exception as e:
            logger.error(f"Error getting articles with summaries without embeddings: {e}")
            return []

    async def count_summary_embeddings(self) -> int:
        """Count articles that have summary embeddings."""
        try:
            count = await self.collection.count_documents({"summary_embedding": {"$exists": True}})
            logger.debug(f"Count query result: {count} articles with summary embeddings")
            return count
        except Exception as e:
            logger.error(f"Error counting articles with summary embeddings: {e}")
            return 0

    async def count_articles_with_summaries(self) -> int:
        """Count articles that have completed summaries."""
        try:
            query = {
                "summary": {"$exists": True, "$ne": None, "$ne": ""},
                "summary_processing_status": "completed"
            }
            count = await self.collection.count_documents(query)
            logger.debug(f"Count query result: {count} articles with completed summaries")
            return count
        except Exception as e:
            logger.error(f"Error counting articles with summaries: {e}")
            return 0

    async def get_todays_articles(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent articles with valid publication_date, ordered by publication_date (newest first).

        Returns a list of dictionaries containing both the Article object and the MongoDB _id.
        """
        try:
            from datetime import datetime, timedelta

            # Get recent articles (last 7 days) that have valid publication_date
            recent_cutoff = datetime.now() - timedelta(days=7)

            # Use publication_date field for filtering and sorting (matching playground query)
            query = {
                "publication_date": {
                    "$exists": True,
                    "$ne": None,
                    "$gte": recent_cutoff,
                    "$type": "date"  # Ensure it's a proper date type
                }
            }

            # Sort by publication_date in MongoDB (newest first) - no frontend sorting
            cursor = self.collection.find(query).sort("publication_date", -1).limit(limit)
            docs = await cursor.to_list(length=limit)

            # Convert to dictionaries with both Article object and _id
            articles = []
            for doc in docs:
                try:
                    # Double-check that the publication_date is valid before including
                    if doc.get("publication_date") and isinstance(doc["publication_date"], datetime):
                        article = Article(**self._clean_article_data(doc))
                        doc_id = str(doc["_id"]) if "_id" in doc else None
                        articles.append({
                            "article": article,
                            "_id": doc_id
                        })
                    else:
                        logger.debug(f"Skipping article with invalid publication_date: {doc.get('url', 'unknown')}")
                        continue
                except Exception as e:
                    logger.warning(f"Error converting article {doc.get('url', 'unknown')}: {e}")
                    continue

            logger.debug(f"Found {len(articles)} articles with valid publication_date, sorted by MongoDB")
            return articles
        except Exception as e:
            logger.error(f"Error getting today's articles: {e}")
            return []

    async def get_articles_without_publication_date(self, limit: int = 100, skip: int = 0) -> List[Article]:
        """Get articles that don't have publication dates yet."""
        try:
            query = {
                "$or": [
                    {"publication_date": {"$exists": False}},
                    {"publication_date": None},
                    {"publication_date": ""}
                ]
            }

            logger.debug(f"Querying articles without publication dates: {query}")
            cursor = self.collection.find(query).skip(skip).limit(limit)
            docs = await cursor.to_list(length=limit)
            logger.debug(f"Found {len(docs)} articles without publication dates")
            return [Article(**self._clean_article_data(doc)) for doc in docs]
        except Exception as e:
            logger.error(f"Error getting articles without publication dates: {e}")
            return []

    async def count_articles_without_publication_date(self) -> int:
        """Count articles that don't have publication dates yet."""
        try:
            query = {
                "$or": [
                    {"publication_date": {"$exists": False}},
                    {"publication_date": None},
                    {"publication_date": ""}
                ]
            }
            count = await self.collection.count_documents(query)
            logger.debug(f"Count query result: {count} articles without publication dates")
            return count
        except Exception as e:
            logger.error(f"Error counting articles without publication dates: {e}")
            return 0

    async def count_articles(self) -> int:
        """Count total articles in the database."""
        try:
            count = await self.collection.count_documents({})
            logger.debug(f"Total articles in database: {count}")
            return count
        except Exception as e:
            logger.error(f"Error counting total articles: {e}")
            return 0

    async def get_articles_with_future_dates(self, current_time: datetime) -> List[Dict[str, Any]]:
        """Get articles with publication dates in the future."""
        try:
            query = {
                "publication_date": {"$gt": current_time}
            }

            logger.debug(f"Querying articles with future dates after {current_time}")
            cursor = self.collection.find(query)
            docs = await cursor.to_list(length=None)  # Get all future-dated articles
            logger.debug(f"Found {len(docs)} articles with future publication dates")
            return docs
        except Exception as e:
            logger.error(f"Error getting articles with future dates: {e}")
            return []

    async def delete_article(self, article_id: str) -> bool:
        """Delete an article by its ID."""
        try:
            from bson import ObjectId
            result = await self.collection.delete_one({"_id": ObjectId(article_id)})
            success = result.deleted_count > 0
            logger.debug(f"Delete article {article_id}: {success}")
            return success
        except Exception as e:
            logger.error(f"Error deleting article {article_id}: {e}")
            return False

    async def update_article_publication_date(self, url: str, publication_date: datetime) -> bool:
        """Update an article with publication date information."""
        try:
            result = await self.collection.update_one(
                {"url": url},
                {
                    "$set": {
                        "publication_date": publication_date
                    }
                }
            )

            if result.modified_count > 0:
                logger.debug(f"Updated publication date for article: {url}")
                return True
            else:
                logger.warning(f"No article found with URL: {url}")
                return False
        except Exception as e:
            logger.error(f"Error updating article publication date for {url}: {e}", exc_info=True)
            return False

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

    async def get_reddit_articles(self, limit: Optional[int] = None, skip: int = 0) -> List[Article]:
        """
        Get articles from Reddit sources that need URL reprocessing.

        Args:
            limit: Maximum number of articles to return
            skip: Number of articles to skip (for pagination)

        Returns:
            List of Reddit articles
        """
        try:
            # Query for articles from Reddit sources
            query = {
                "origin": {"$regex": "reddit\\.com", "$options": "i"}
            }

            cursor = self.collection.find(query).sort("publication_date", DESCENDING)

            if skip > 0:
                cursor = cursor.skip(skip)
            if limit:
                cursor = cursor.limit(limit)

            docs = await cursor.to_list(length=None)

            # Clean and convert to Article objects
            articles = []
            for doc in docs:
                doc = self._clean_article_data(doc)
                articles.append(Article(**doc))

            logger.info(f"Found {len(articles)} Reddit articles (limit={limit}, skip={skip})")
            return articles

        except Exception as e:
            logger.error(f"Error getting Reddit articles: {e}")
            return []

    async def count_reddit_articles(self) -> int:
        """Count total number of Reddit articles."""
        try:
            query = {
                "origin": {"$regex": "reddit\\.com", "$options": "i"}
            }
            count = await self.collection.count_documents(query)
            logger.info(f"Total Reddit articles: {count}")
            return count
        except Exception as e:
            logger.error(f"Error counting Reddit articles: {e}")
            return 0

    async def update_article_url(self, old_url: str, new_url: str) -> bool:
        """
        Update an article's URL.

        Args:
            old_url: Current article URL
            new_url: New article URL

        Returns:
            True if update was successful, False otherwise
        """
        try:
            result = await self.collection.update_one(
                {"url": old_url},
                {"$set": {"url": new_url}}
            )

            if result.modified_count > 0:
                logger.info(f"Updated article URL: {old_url} -> {new_url}")
                return True
            else:
                logger.warning(f"No article found with URL: {old_url}")
                return False

        except Exception as e:
            logger.error(f"Error updating article URL {old_url}: {e}")
            return False


# Global repository instance
article_repository = ArticleRepository()

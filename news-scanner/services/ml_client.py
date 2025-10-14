"""
ML Service Client - HTTP client for communicating with the ML service.

This client handles all communication with the dedicated ML service,
allowing the main application to perform ML operations without
having ML dependencies installed locally.
"""

import logging
import aiohttp
from typing import List, Dict, Any, Optional
from config import settings

logger = logging.getLogger(__name__)


class MLServiceClient:
    """Client for communicating with the ML service."""

    def __init__(self, ml_service_url: str = None):
        """
        Initialize the ML service client.

        Args:
            ml_service_url: URL of the ML service (defaults to settings)
        """
        self.ml_service_url = ml_service_url or settings.ml_service_url
        self.session = None
        self._loop = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session, handling event loop changes."""
        import asyncio
        current_loop = asyncio.get_event_loop()

        # If session exists but is from a different loop, close it
        if self.session is not None and self._loop is not current_loop:
            try:
                if not self.session.closed:
                    await self.session.close()
            except:
                pass
            self.session = None

        # Create new session if needed
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
            self._loop = current_loop

        return self.session

    async def close(self):
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def health_check(self) -> bool:
        """Check if ML service is healthy."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.ml_service_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("status") == "healthy"
                return False
        except Exception as e:
            logger.error(f"ML service health check failed: {e}")
            return False

    async def generate_embedding(self, text: str, article_id: str = None) -> Optional[List[float]]:
        """
        Generate embedding for text.

        Args:
            text: Text to generate embedding for
            article_id: Optional article ID

        Returns:
            Embedding vector or None if failed
        """
        try:
            session = await self._get_session()
            payload = {
                "text": text,
                "article_id": article_id
            }

            async with session.post(
                f"{self.ml_service_url}/embeddings/generate",
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("embedding")
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to generate embedding: {error_text}")
                    return None

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None

    def generate_embedding_sync(self, text: str, article_id: str = None) -> Optional[List[float]]:
        """
        Synchronous version of generate_embedding for use in Celery tasks.

        Args:
            text: Text to generate embedding for
            article_id: Optional article ID

        Returns:
            Embedding vector or None if failed
        """
        import requests
        import time

        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                # First check if ML service is healthy
                try:
                    health_response = requests.get(f"{self.ml_service_url}/health", timeout=5)
                    if health_response.status_code != 200:
                        logger.warning(f"ML service health check failed (attempt {attempt + 1}/{max_retries})")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            continue
                        return None
                except Exception as health_e:
                    logger.warning(f"ML service health check exception (attempt {attempt + 1}/{max_retries}): {health_e}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return None

                logger.info(f"Calling ML service for embedding, text length: {len(text)}, article_id: {article_id}")
                payload = {
                    "text": text,
                    "article_id": article_id
                }

                response = requests.post(
                    f"{self.ml_service_url}/embeddings/generate",
                    json=payload,
                    timeout=30
                )

                logger.info(f"ML service response status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    embedding = data.get("embedding")
                    if embedding:
                        logger.info(f"Successfully generated embedding with {len(embedding)} dimensions")
                        return embedding
                    else:
                        logger.error("No embedding in successful response")
                        return None
                else:
                    logger.error(f"Failed to generate embedding: HTTP {response.status_code} - {response.text}")
                    return None

            except Exception as e:
                logger.error(f"Exception during embedding generation (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                import traceback
                logger.error(f"Final exception traceback: {traceback.format_exc()}")
                return None

        return None

    async def batch_generate_embeddings(self, batch_size: int = 100) -> Dict[str, Any]:
        """
        Generate embeddings for multiple articles.

        Args:
            batch_size: Number of articles to process in batch

        Returns:
            Batch processing results
        """
        try:
            session = await self._get_session()
            params = {"batch_size": batch_size}

            async with session.post(
                f"{self.ml_service_url}/embeddings/batch",
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to batch generate embeddings: {error_text}")
                    return {"success": False, "error": error_text}

        except Exception as e:
            logger.error(f"Error in batch embedding generation: {e}")
            return {"success": False, "error": str(e)}

    async def find_similar_articles(
        self,
        article: Dict[str, Any],
        limit: int = 10,
        similarity_threshold: float = 0.7,
        exclude_self: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Find articles similar to the given article.

        Args:
            article: Article to find similar articles for
            limit: Maximum number of similar articles to return
            similarity_threshold: Minimum similarity threshold
            exclude_self: Whether to exclude the article itself

        Returns:
            List of similar articles
        """
        try:
            session = await self._get_session()
            payload = {
                "article": article,
                "limit": limit,
                "similarity_threshold": similarity_threshold,
                "exclude_self": exclude_self
            }

            async with session.post(
                f"{self.ml_service_url}/similarity/search",
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("similar_articles", [])
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to find similar articles: {error_text}")
                    return []

        except Exception as e:
            logger.error(f"Error finding similar articles: {e}")
            return []

    async def analyze_article_topics(self, article_url: str) -> Dict[str, Any]:
        """
        Analyze topics for an article.

        Args:
            article_url: URL of the article to analyze

        Returns:
            Topic analysis results
        """
        try:
            session = await self._get_session()
            payload = {"article_url": article_url}

            async with session.post(
                f"{self.ml_service_url}/topics/analyze",
                json=payload
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to analyze topics: {error_text}")
                    return {"success": False, "error": error_text}

        except Exception as e:
            logger.error(f"Error analyzing topics: {e}")
            return {"success": False, "error": str(e)}

    async def group_articles_by_topics(
        self,
        similarity_threshold: float = 0.75,
        min_group_size: int = 2
    ) -> Dict[str, Any]:
        """
        Group articles by topics.

        Args:
            similarity_threshold: Similarity threshold for grouping
            min_group_size: Minimum group size

        Returns:
            Topic grouping results
        """
        try:
            session = await self._get_session()
            params = {
                "similarity_threshold": similarity_threshold,
                "min_group_size": min_group_size
            }

            async with session.post(
                f"{self.ml_service_url}/topics/group",
                params=params
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to group articles by topics: {error_text}")
                    return {"success": False, "error": error_text}

        except Exception as e:
            logger.error(f"Error grouping articles by topics: {e}")
            return {"success": False, "error": str(e)}

    async def get_similar_articles_for_display(
        self,
        article_url: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get similar articles formatted for frontend display.

        Args:
            article_url: URL of the article to find similar articles for
            limit: Maximum number of similar articles to return

        Returns:
            List of similar articles with metadata for display
        """
        try:
            session = await self._get_session()
            payload = {
                "article_url": article_url,
                "limit": limit
            }

            async with session.post(
                f"{self.ml_service_url}/topics/similar-for-display",
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("similar_articles", [])
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to get similar articles for display: {error_text}")
                    return []

        except Exception as e:
            logger.error(f"Error getting similar articles for display: {e}")
            return []

    async def get_article_topics(self, article_url: str) -> List[Dict[str, Any]]:
        """
        Get topic groups that contain the specified article.

        Args:
            article_url: URL of the article

        Returns:
            List of topic groups containing the article
        """
        try:
            session = await self._get_session()
            payload = {"article_url": article_url}

            async with session.post(
                f"{self.ml_service_url}/topics/article-topics",
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("topic_groups", [])
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to get article topics: {error_text}")
                    return []

        except Exception as e:
            logger.error(f"Error getting article topics: {e}")
            return []

    async def generate_summary_embedding(self, summary_text: str, article_url: str = None) -> Optional[List[float]]:
        """
        Generate embedding for summary text.

        Args:
            summary_text: Summary text to generate embedding for
            article_url: Optional article URL for logging

        Returns:
            Embedding vector or None if failed
        """
        try:
            session = await self._get_session()
            payload = {
                "summary_text": summary_text,
                "article_url": article_url
            }

            async with session.post(
                f"{self.ml_service_url}/embeddings/summary/generate",
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("embedding")
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to generate summary embedding: {error_text}")
                    return None

        except Exception as e:
            logger.error(f"Error generating summary embedding: {e}")
            return None

    def generate_summary_embedding_sync(self, summary_text: str, article_url: str = None) -> Optional[List[float]]:
        """
        Synchronous version of generate_summary_embedding for use in Celery tasks.

        Args:
            summary_text: Summary text to generate embedding for
            article_url: Optional article URL for logging

        Returns:
            Embedding vector or None if failed
        """
        import requests
        import time

        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                # First check if ML service is healthy
                try:
                    health_response = requests.get(f"{self.ml_service_url}/health", timeout=5)
                    if health_response.status_code != 200:
                        logger.warning(f"ML service health check failed (attempt {attempt + 1}/{max_retries})")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            continue
                        return None
                except Exception as health_e:
                    logger.warning(f"ML service health check exception (attempt {attempt + 1}/{max_retries}): {health_e}")
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        continue
                    return None

                logger.info(f"Calling ML service for summary embedding, text length: {len(summary_text)}, article_url: {article_url}")
                payload = {
                    "summary_text": summary_text,
                    "article_url": article_url
                }

                response = requests.post(
                    f"{self.ml_service_url}/embeddings/summary/generate",
                    json=payload,
                    timeout=30
                )

                logger.info(f"ML service response status: {response.status_code}")
                if response.status_code == 200:
                    data = response.json()
                    embedding = data.get("embedding")
                    if embedding:
                        logger.info(f"Successfully generated summary embedding with {len(embedding)} dimensions")
                        return embedding
                    else:
                        logger.error("No embedding in successful response")
                        return None
                else:
                    logger.error(f"Failed to generate summary embedding: HTTP {response.status_code} - {response.text}")
                    return None

            except Exception as e:
                logger.error(f"Exception during summary embedding generation (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                import traceback
                logger.error(f"Final exception traceback: {traceback.format_exc()}")
                return None

        return None

    async def generate_daily_topics(
        self,
        days_back: int = 7,
        similarity_threshold: float = 0.75,
        min_group_size: int = 3,
        max_articles: int = 500
    ) -> Dict[str, Any]:
        """
        Generate daily topic groups using ML service.

        Args:
            days_back: Number of days back to fetch articles
            similarity_threshold: Minimum similarity for grouping
            min_group_size: Minimum articles per group
            max_articles: Maximum articles to process (for performance)

        Returns:
            Topic grouping results
        """
        try:
            session = await self._get_session()
            payload = {
                "days_back": days_back,
                "similarity_threshold": similarity_threshold,
                "min_group_size": min_group_size,
                "max_articles": max_articles
            }

            async with session.post(
                f"{self.ml_service_url}/topics/generate-daily-topics",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=300)  # 5 minutes for large datasets
            ) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to generate daily topics: {error_text}")
                    return {"success": False, "error": error_text}

        except Exception as e:
            logger.error(f"Error generating daily topics: {e}")
            return {"success": False, "error": str(e)}

    async def find_similar_articles_by_summary(
        self,
        article_url: str,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Find articles similar to the given article based on summary embeddings.

        Args:
            article_url: URL of the article to find similar articles for
            limit: Maximum number of similar articles to return
            similarity_threshold: Minimum similarity threshold

        Returns:
            List of similar articles
        """
        try:
            session = await self._get_session()
            payload = {
                "article_url": article_url,
                "limit": limit,
                "similarity_threshold": similarity_threshold
            }

            async with session.post(
                f"{self.ml_service_url}/similarity/search-by-summary",
                json=payload
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("similar_articles", [])
                else:
                    error_text = await response.text()
                    logger.error(f"Failed to find similar articles by summary: {error_text}")
                    return []

        except Exception as e:
            logger.error(f"Error finding similar articles by summary: {e}")
            return []

    async def get_similar_articles_by_summary_for_display(
        self,
        article_url: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get similar articles by summary formatted for frontend display.

        Args:
            article_url: URL of the article to find similar articles for
            limit: Maximum number of similar articles to return

        Returns:
            List of similar articles with metadata for display
        """
        try:
            # Find similar articles by summary
            similar_articles = await self.find_similar_articles_by_summary(
                article_url,
                limit=limit,
                similarity_threshold=0.6
            )

            # Format for display
            formatted_articles = []
            for item in similar_articles:
                article = item.get("article", {})
                formatted_articles.append({
                    "url": article.get("url", ""),
                    "title": article.get("title", ""),
                    "host": article.get("Host", ""),
                    "publication_date": article.get("publication_date"),
                    "similarity_score": item.get("similarity_score", 0),
                    "preview": article.get("summary", "")[:200] + "..." if article.get("summary") else ""
                })

            return formatted_articles

        except Exception as e:
            logger.error(f"Error getting similar articles by summary for display: {e}")
            return []


# Global ML service client instance
ml_client = MLServiceClient()

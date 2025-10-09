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

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
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


# Global ML service client instance
ml_client = MLServiceClient()

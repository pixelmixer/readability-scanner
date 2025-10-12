"""
Vector similarity service for article topic analysis.
"""

import logging
import numpy as np
import torch
from typing import List, Dict, Any, Optional, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from pymongo import ASCENDING
import asyncio
from datetime import datetime

from database.connection import db_manager
from models.article import Article

logger = logging.getLogger(__name__)


class VectorSimilarityService:
    """Service for generating embeddings and finding similar articles."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the vector similarity service.

        Args:
            model_name: Name of the sentence transformer model to use
        """
        self.model_name = model_name
        self.model = None
        self.embedding_dimension = 384  # Dimension for all-MiniLM-L6-v2
        self.collection_name = "documents"
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    async def initialize(self):
        """Initialize the embedding model."""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            logger.info(f"Using device: {self.device}")
            self.model = SentenceTransformer(self.model_name)
            self.model = self.model.to(self.device)
            logger.info(f"Embedding model loaded successfully on {self.device}")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise

    def _prepare_text_for_embedding(self, article: Dict[str, Any]) -> str:
        """
        Prepare article text for embedding generation.

        Args:
            article: Article document from MongoDB

        Returns:
            Combined text for embedding
        """
        # Combine title and content for better semantic representation
        title = article.get('title', '') or ''
        content = article.get('Cleaned Data', '') or article.get('content', '') or ''

        # Use cleaned data if available, otherwise use raw content
        text_parts = []

        if title:
            text_parts.append(title)

        if content:
            # Limit content length to avoid memory issues
            max_content_length = 2000
            if len(content) > max_content_length:
                content = content[:max_content_length] + "..."
            text_parts.append(content)

        return " ".join(text_parts).strip()

    async def generate_embedding(self, article: Dict[str, Any]) -> Optional[List[float]]:
        """
        Generate embedding for a single article.

        Args:
            article: Article document from MongoDB

        Returns:
            Embedding vector or None if failed
        """
        try:
            if not self.model:
                await self.initialize()

            text = self._prepare_text_for_embedding(article)
            if not text:
                logger.warning(f"No text content found for article: {article.get('url', 'unknown')}")
                return None

            # Generate embedding
            embedding = self.model.encode(text, convert_to_tensor=False)
            return embedding.tolist()

        except Exception as e:
            logger.error(f"Failed to generate embedding for article {article.get('url', 'unknown')}: {e}")
            return None

    async def store_embedding(self, article_id: str, embedding: List[float]) -> bool:
        """
        Store embedding in MongoDB document.

        Args:
            article_id: MongoDB document ID or URL
            embedding: Embedding vector

        Returns:
            True if successful
        """
        try:
            db = db_manager.get_database()
            collection = db[self.collection_name]

            # Update document with embedding
            result = await collection.update_one(
                {"url": article_id},  # Using URL as identifier
                {
                    "$set": {
                        "embedding": embedding,
                        "embedding_updated_at": datetime.utcnow(),
                        "embedding_model": self.model_name
                    }
                }
            )

            if result.modified_count > 0:
                logger.debug(f"Stored embedding for article: {article_id}")
                return True
            else:
                logger.warning(f"No document updated for article: {article_id}")
                return False

        except Exception as e:
            logger.error(f"Failed to store embedding for article {article_id}: {e}")
            return False

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
            article: Article document to find similar articles for
            limit: Maximum number of similar articles to return
            similarity_threshold: Minimum similarity score (0-1)
            exclude_self: Whether to exclude the source article from results

        Returns:
            List of similar articles with similarity scores
        """
        try:
            # Generate embedding for the query article
            query_embedding = await self.generate_embedding(article)
            if not query_embedding:
                logger.warning("Failed to generate embedding for query article")
                return []

            # Get all articles with embeddings
            db = db_manager.get_database()
            collection = db[self.collection_name]

            # Find articles that have embeddings
            cursor = collection.find(
                {"embedding": {"$exists": True}},
                {
                    "url": 1,
                    "title": 1,
                    "Cleaned Data": 1,
                    "content": 1,
                    "publication_date": 1,
                    "Host": 1,
                    "embedding": 1,
                    "_id": 1
                }
            )

            articles_with_embeddings = await cursor.to_list(length=None)

            if not articles_with_embeddings:
                logger.warning("No articles with embeddings found")
                return []

            # Calculate similarities
            similarities = []
            query_embedding_array = np.array(query_embedding).reshape(1, -1)

            for doc in articles_with_embeddings:
                # Skip self if requested
                if exclude_self and doc.get('url') == article.get('url'):
                    continue

                doc_embedding = doc.get('embedding')
                if not doc_embedding:
                    continue

                # Calculate cosine similarity
                doc_embedding_array = np.array(doc_embedding).reshape(1, -1)
                similarity = cosine_similarity(query_embedding_array, doc_embedding_array)[0][0]

                if similarity >= similarity_threshold:
                    similarities.append({
                        'article': doc,
                        'similarity_score': float(similarity)
                    })

            # Sort by similarity score (descending)
            similarities.sort(key=lambda x: x['similarity_score'], reverse=True)

            # Return top results
            return similarities[:limit]

        except Exception as e:
            logger.error(f"Failed to find similar articles: {e}")
            return []

    async def find_similar_articles_by_url(
        self,
        article_url: str,
        limit: int = 10,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Find articles similar to the article with the given URL.

        Args:
            article_url: URL of the article to find similar articles for
            limit: Maximum number of similar articles to return
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of similar articles with similarity scores
        """
        try:
            # Get the article by URL
            db = db_manager.get_database()
            collection = db[self.collection_name]

            article = await collection.find_one({"url": article_url})
            if not article:
                logger.warning(f"Article not found: {article_url}")
                return []

            return await self.find_similar_articles(article, limit, similarity_threshold)

        except Exception as e:
            logger.error(f"Failed to find similar articles for URL {article_url}: {e}")
            return []

    async def batch_generate_embeddings(self, batch_size: int = 100) -> Dict[str, int]:
        """
        Generate embeddings for all articles that don't have them.

        Args:
            batch_size: Number of articles to process in each batch

        Returns:
            Dictionary with processing statistics
        """
        try:
            db = db_manager.get_database()
            collection = db[self.collection_name]

            # Find articles without embeddings
            cursor = collection.find(
                {
                    "embedding": {"$exists": False},
                    "$or": [
                        {"Cleaned Data": {"$exists": True, "$ne": ""}},
                        {"content": {"$exists": True, "$ne": ""}}
                    ]
                },
                {
                    "url": 1,
                    "title": 1,
                    "Cleaned Data": 1,
                    "content": 1
                }
            )

            articles_to_process = await cursor.to_list(length=None)
            total_articles = len(articles_to_process)

            logger.info(f"Found {total_articles} articles without embeddings")

            processed = 0
            failed = 0

            # Process in batches
            for i in range(0, total_articles, batch_size):
                batch = articles_to_process[i:i + batch_size]

                for article in batch:
                    try:
                        embedding = await self.generate_embedding(article)
                        if embedding:
                            success = await self.store_embedding(article['url'], embedding)
                            if success:
                                processed += 1
                            else:
                                failed += 1
                        else:
                            failed += 1
                    except Exception as e:
                        logger.error(f"Failed to process article {article.get('url', 'unknown')}: {e}")
                        failed += 1

                # Log progress
                if (i + batch_size) % (batch_size * 5) == 0:
                    logger.info(f"Processed {i + batch_size}/{total_articles} articles")

            logger.info(f"Batch embedding generation completed. Processed: {processed}, Failed: {failed}")

            return {
                "total_articles": total_articles,
                "processed": processed,
                "failed": failed
            }

        except Exception as e:
            logger.error(f"Failed to batch generate embeddings: {e}")
            return {"total_articles": 0, "processed": 0, "failed": 0}

    async def generate_summary_embedding(self, summary_text: str) -> Optional[List[float]]:
        """
        Generate embedding for a summary text.

        Args:
            summary_text: Summary text to generate embedding for

        Returns:
            Embedding vector or None if failed
        """
        try:
            if not self.model:
                await self.initialize()

            if not summary_text or not summary_text.strip():
                logger.warning("No summary text provided for embedding generation")
                return None

            # Generate embedding from summary text
            embedding = self.model.encode(summary_text.strip(), convert_to_tensor=False)
            return embedding.tolist()

        except Exception as e:
            logger.error(f"Failed to generate summary embedding: {e}")
            return None

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
            similarity_threshold: Minimum similarity score (0-1)

        Returns:
            List of similar articles with similarity scores
        """
        try:
            # Get the article by URL
            db = db_manager.get_database()
            collection = db[self.collection_name]

            article = await collection.find_one({"url": article_url})
            if not article:
                logger.warning(f"Article not found: {article_url}")
                return []

            # Get the article's summary embedding
            query_embedding = article.get("summary_embedding")
            if not query_embedding:
                logger.warning(f"Article does not have a summary embedding: {article_url}")
                return []

            # Find articles that have summary embeddings
            cursor = collection.find(
                {"summary_embedding": {"$exists": True}},
                {
                    "url": 1,
                    "title": 1,
                    "summary": 1,
                    "publication_date": 1,
                    "Host": 1,
                    "summary_embedding": 1,
                    "_id": 1
                }
            )

            articles_with_embeddings = await cursor.to_list(length=None)

            if not articles_with_embeddings:
                logger.warning("No articles with summary embeddings found")
                return []

            # Calculate similarities
            similarities = []
            query_embedding_array = np.array(query_embedding).reshape(1, -1)

            for doc in articles_with_embeddings:
                # Skip self
                if doc.get('url') == article_url:
                    continue

                doc_embedding = doc.get('summary_embedding')
                if not doc_embedding:
                    continue

                # Calculate cosine similarity
                doc_embedding_array = np.array(doc_embedding).reshape(1, -1)
                similarity = cosine_similarity(query_embedding_array, doc_embedding_array)[0][0]

                if similarity >= similarity_threshold:
                    similarities.append({
                        'article': doc,
                        'similarity_score': float(similarity)
                    })

            # Sort by similarity score (descending)
            similarities.sort(key=lambda x: x['similarity_score'], reverse=True)

            # Return top results
            return similarities[:limit]

        except Exception as e:
            logger.error(f"Failed to find similar articles by summary for URL {article_url}: {e}")
            return []

    async def create_vector_index(self) -> bool:
        """
        Create a vector search index in MongoDB.
        Note: This requires MongoDB Atlas or MongoDB 7.0+ with vector search support.

        Returns:
            True if successful
        """
        try:
            db = db_manager.get_database()
            collection = db[self.collection_name]

            # Create a 2dsphere index for vector search (if supported)
            # This is a simplified approach - in production, you'd use MongoDB Atlas Vector Search
            index_spec = [
                ("embedding", ASCENDING)
            ]

            await collection.create_index(index_spec)
            logger.info("Vector index created successfully")
            return True

        except Exception as e:
            logger.warning(f"Vector index creation failed (may not be supported in local MongoDB): {e}")
            return False


# Global instance
vector_service = VectorSimilarityService()

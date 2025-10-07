"""
Topic grouping and shared summary service.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from collections import defaultdict
import asyncio

from database.connection import db_manager
from services.vector_service import vector_service
from services.summary_service import SummaryService

logger = logging.getLogger(__name__)


class TopicService:
    """Service for grouping articles by topics and generating shared summaries."""

    def __init__(self):
        self.collection_name = "documents"
        self.topics_collection_name = "article_topics"
        self.summary_service = SummaryService()

    async def group_articles_by_topics(
        self,
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
            db = db_manager.get_database()
            collection = db[self.collection_name]

            # Get all articles with embeddings
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

            articles = await cursor.to_list(length=None)
            logger.info(f"Processing {len(articles)} articles for topic grouping")

            # Group articles by similarity
            topic_groups = []
            processed_articles = set()

            for i, article in enumerate(articles):
                if article['url'] in processed_articles:
                    continue

                # Find similar articles
                similar_articles = await vector_service.find_similar_articles(
                    article,
                    limit=50,  # Get more candidates
                    similarity_threshold=similarity_threshold,
                    exclude_self=False  # Include self in results
                )

                if len(similar_articles) >= min_group_size:
                    # Create topic group
                    topic_group = {
                        "topic_id": f"topic_{len(topic_groups) + 1}",
                        "articles": [sim['article'] for sim in similar_articles],
                        "similarity_scores": [sim['similarity_score'] for sim in similar_articles],
                        "created_at": datetime.utcnow(),
                        "article_count": len(similar_articles)
                    }

                    # Mark articles as processed
                    for sim_article in similar_articles:
                        processed_articles.add(sim_article['article']['url'])

                    topic_groups.append(topic_group)
                    logger.info(f"Created topic group {topic_group['topic_id']} with {len(similar_articles)} articles")

            # Store topic groups in database
            await self._store_topic_groups(topic_groups)

            logger.info(f"Topic grouping completed. Created {len(topic_groups)} topic groups")

            return {
                "total_articles": len(articles),
                "processed_articles": len(processed_articles),
                "topic_groups": len(topic_groups),
                "average_group_size": sum(len(group['articles']) for group in topic_groups) / len(topic_groups) if topic_groups else 0
            }

        except Exception as e:
            logger.error(f"Failed to group articles by topics: {e}")
            return {"error": str(e)}

    async def _store_topic_groups(self, topic_groups: List[Dict[str, Any]]) -> None:
        """Store topic groups in the database."""
        try:
            db = db_manager.get_database()
            topics_collection = db[self.topics_collection_name]

            # Clear existing topic groups
            await topics_collection.delete_many({})

            # Insert new topic groups
            if topic_groups:
                await topics_collection.insert_many(topic_groups)
                logger.info(f"Stored {len(topic_groups)} topic groups in database")

        except Exception as e:
            logger.error(f"Failed to store topic groups: {e}")

    async def generate_shared_summaries(self) -> Dict[str, Any]:
        """
        Generate shared summaries for all topic groups.

        Returns:
            Dictionary with summary generation statistics
        """
        try:
            db = db_manager.get_database()
            topics_collection = db[self.topics_collection_name]

            # Get all topic groups
            cursor = topics_collection.find({})
            topic_groups = await cursor.to_list(length=None)

            if not topic_groups:
                logger.warning("No topic groups found for summary generation")
                return {"error": "No topic groups found"}

            generated_summaries = 0
            failed_summaries = 0

            for topic_group in topic_groups:
                try:
                    # Generate shared summary for this topic group
                    shared_summary = await self._generate_topic_summary(topic_group)

                    if shared_summary:
                        # Update topic group with shared summary
                        await topics_collection.update_one(
                            {"topic_id": topic_group["topic_id"]},
                            {
                                "$set": {
                                    "shared_summary": shared_summary,
                                    "summary_generated_at": datetime.utcnow(),
                                    "summary_status": "completed"
                                }
                            }
                        )
                        generated_summaries += 1
                        logger.info(f"Generated shared summary for topic {topic_group['topic_id']}")
                    else:
                        failed_summaries += 1
                        logger.warning(f"Failed to generate summary for topic {topic_group['topic_id']}")

                except Exception as e:
                    logger.error(f"Error generating summary for topic {topic_group['topic_id']}: {e}")
                    failed_summaries += 1

            logger.info(f"Shared summary generation completed. Generated: {generated_summaries}, Failed: {failed_summaries}")

            return {
                "total_topics": len(topic_groups),
                "generated_summaries": generated_summaries,
                "failed_summaries": failed_summaries
            }

        except Exception as e:
            logger.error(f"Failed to generate shared summaries: {e}")
            return {"error": str(e)}

    async def _generate_topic_summary(self, topic_group: Dict[str, Any]) -> Optional[str]:
        """
        Generate a shared summary for a topic group.

        Args:
            topic_group: Topic group with articles

        Returns:
            Generated summary or None if failed
        """
        try:
            articles = topic_group.get("articles", [])
            if not articles:
                return None

            # Combine content from all articles in the topic
            combined_content = []

            for article in articles:
                title = article.get('title', '')
                content = article.get('Cleaned Data', '') or article.get('content', '')

                if title:
                    combined_content.append(f"Title: {title}")
                if content:
                    # Limit content length per article
                    max_length = 500
                    if len(content) > max_length:
                        content = content[:max_length] + "..."
                    combined_content.append(f"Content: {content}")

            if not combined_content:
                logger.warning(f"No content found for topic group {topic_group['topic_id']}")
                return None

            # Join all content
            full_content = "\n\n".join(combined_content)

            # Limit total content length for summary generation
            max_total_length = 4000
            if len(full_content) > max_total_length:
                full_content = full_content[:max_total_length] + "..."

            # Generate summary using the existing summary service
            summary = await self.summary_service.generate_summary(full_content)

            return summary

        except Exception as e:
            logger.error(f"Failed to generate topic summary: {e}")
            return None

    async def get_article_topics(self, article_url: str) -> List[Dict[str, Any]]:
        """
        Get topic groups that contain the specified article.

        Args:
            article_url: URL of the article

        Returns:
            List of topic groups containing the article
        """
        try:
            db = db_manager.get_database()
            topics_collection = db[self.topics_collection_name]

            # Find topic groups containing this article
            cursor = topics_collection.find(
                {"articles.url": article_url},
                {
                    "topic_id": 1,
                    "shared_summary": 1,
                    "summary_generated_at": 1,
                    "article_count": 1,
                    "created_at": 1
                }
            )

            topic_groups = await cursor.to_list(length=None)
            return topic_groups

        except Exception as e:
            logger.error(f"Failed to get article topics for {article_url}: {e}")
            return []

    async def get_similar_articles_for_display(
        self,
        article_url: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get similar articles for frontend display.

        Args:
            article_url: URL of the article
            limit: Maximum number of similar articles to return

        Returns:
            List of similar articles with metadata
        """
        try:
            # Get similar articles using vector similarity
            similar_articles = await vector_service.find_similar_articles_by_url(
                article_url,
                limit=limit,
                similarity_threshold=0.6  # Lower threshold for display
            )

            # Format for frontend display
            formatted_articles = []
            for sim_article in similar_articles:
                article = sim_article['article']
                formatted_articles.append({
                    "url": article.get('url'),
                    "title": article.get('title', 'Untitled'),
                    "host": article.get('Host', ''),
                    "publication_date": article.get('publication_date'),
                    "similarity_score": sim_article['similarity_score'],
                    "preview": self._generate_preview(article)
                })

            return formatted_articles

        except Exception as e:
            logger.error(f"Failed to get similar articles for display: {e}")
            return []

    def _generate_preview(self, article: Dict[str, Any], max_length: int = 150) -> str:
        """
        Generate a preview text for an article.

        Args:
            article: Article document
            max_length: Maximum length of preview

        Returns:
            Preview text
        """
        content = article.get('Cleaned Data', '') or article.get('content', '')
        if not content:
            return "No preview available"

        # Clean and truncate content
        preview = content.strip()
        if len(preview) > max_length:
            preview = preview[:max_length].rsplit(' ', 1)[0] + "..."

        return preview


# Global instance
topic_service = TopicService()

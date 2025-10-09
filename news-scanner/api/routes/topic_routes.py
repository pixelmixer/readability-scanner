"""
API routes for topic analysis and similar articles.
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel

from services.ml_client import ml_client
from database.connection import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/topics", tags=["topics"])


def _generate_preview(article: Dict[str, Any], max_length: int = 150) -> str:
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


class SimilarArticleResponse(BaseModel):
    """Response model for similar articles."""
    url: str
    title: str
    host: str
    publication_date: Optional[str]
    similarity_score: float
    preview: str


class TopicGroupResponse(BaseModel):
    """Response model for topic groups."""
    topic_id: str
    article_count: int
    shared_summary: Optional[str]
    summary_generated_at: Optional[str]
    created_at: str


class SimilarArticlesResponse(BaseModel):
    """Response model for similar articles endpoint."""
    article_url: str
    similar_articles: List[SimilarArticleResponse]
    total_found: int


@router.get("/similar/{article_url:path}", response_model=SimilarArticlesResponse)
async def get_similar_articles(
    article_url: str,
    limit: int = Query(5, ge=1, le=20, description="Maximum number of similar articles to return"),
    similarity_threshold: float = Query(0.6, ge=0.0, le=1.0, description="Minimum similarity score"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get articles similar to the specified article.

    Args:
        article_url: URL of the article to find similar articles for
        limit: Maximum number of similar articles to return
        similarity_threshold: Minimum similarity score (0-1)
        db: Database connection

    Returns:
        List of similar articles with metadata
    """
    try:
        # Check if article exists
        collection = db["documents"]
        article = await collection.find_one({"url": article_url})
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")

        # Get similar articles
        similar_articles = await ml_client.get_similar_articles_for_display(
            article_url,
            limit=limit
        )

        # Filter by similarity threshold
        filtered_articles = [
            article for article in similar_articles
            if article["similarity_score"] >= similarity_threshold
        ]

        return SimilarArticlesResponse(
            article_url=article_url,
            similar_articles=[
                SimilarArticleResponse(
                    url=article["url"],
                    title=article["title"],
                    host=article["host"],
                    publication_date=article["publication_date"].isoformat() if article["publication_date"] else None,
                    similarity_score=article["similarity_score"],
                    preview=article["preview"]
                )
                for article in filtered_articles
            ],
            total_found=len(filtered_articles)
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting similar articles for {article_url}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/article/{article_url:path}/topics", response_model=List[TopicGroupResponse])
async def get_article_topics(
    article_url: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get topic groups that contain the specified article.

    Args:
        article_url: URL of the article
        db: Database connection

    Returns:
        List of topic groups containing the article
    """
    try:
        # Check if article exists
        collection = db["documents"]
        article = await collection.find_one({"url": article_url})
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")

        # Get topic groups
        topic_groups = await ml_client.get_article_topics(article_url)

        return [
            TopicGroupResponse(
                topic_id=topic["topic_id"],
                article_count=topic["article_count"],
                shared_summary=topic.get("shared_summary"),
                summary_generated_at=topic.get("summary_generated_at").isoformat() if topic.get("summary_generated_at") else None,
                created_at=topic["created_at"].isoformat()
            )
            for topic in topic_groups
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting article topics for {article_url}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/groups", response_model=List[TopicGroupResponse])
async def get_all_topic_groups(
    limit: int = Query(50, ge=1, le=200, description="Maximum number of topic groups to return"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get all topic groups.

    Args:
        limit: Maximum number of topic groups to return
        db: Database connection

    Returns:
        List of all topic groups
    """
    try:
        topics_collection = db["article_topics"]

        cursor = topics_collection.find({}).sort("created_at", -1).limit(limit)
        topic_groups = await cursor.to_list(length=limit)

        return [
            TopicGroupResponse(
                topic_id=topic["topic_id"],
                article_count=topic["article_count"],
                shared_summary=topic.get("shared_summary"),
                summary_generated_at=topic.get("summary_generated_at").isoformat() if topic.get("summary_generated_at") else None,
                created_at=topic["created_at"].isoformat()
            )
            for topic in topic_groups
        ]

    except Exception as e:
        logger.error(f"Error getting all topic groups: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/groups/{topic_id}")
async def get_topic_group_details(
    topic_id: str,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Get detailed information about a specific topic group.

    Args:
        topic_id: ID of the topic group
        db: Database connection

    Returns:
        Detailed topic group information including articles
    """
    try:
        topics_collection = db["article_topics"]

        topic_group = await topics_collection.find_one({"topic_id": topic_id})
        if not topic_group:
            raise HTTPException(status_code=404, detail="Topic group not found")

        # Format articles for response
        articles = []
        for article in topic_group.get("articles", []):
            articles.append({
                "url": article.get("url"),
                "title": article.get("title", "Untitled"),
                "host": article.get("Host", ""),
                "publication_date": article.get("publication_date").isoformat() if article.get("publication_date") else None,
                "preview": _generate_preview(article)
            })

        return {
            "topic_id": topic_group["topic_id"],
            "article_count": topic_group["article_count"],
            "shared_summary": topic_group.get("shared_summary"),
            "summary_generated_at": topic_group.get("summary_generated_at").isoformat() if topic_group.get("summary_generated_at") else None,
            "created_at": topic_group["created_at"].isoformat(),
            "articles": articles,
            "similarity_scores": topic_group.get("similarity_scores", [])
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting topic group details for {topic_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats")
async def get_topic_analysis_stats(db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Get statistics about topic analysis.

    Args:
        db: Database connection

    Returns:
        Topic analysis statistics
    """
    try:
        # Get article statistics
        collection = db["documents"]
        total_articles = await collection.count_documents({})
        articles_with_embeddings = await collection.count_documents({"embedding": {"$exists": True}})

        # Get topic group statistics
        topics_collection = db["article_topics"]
        total_topic_groups = await topics_collection.count_documents({})
        topic_groups_with_summaries = await topics_collection.count_documents({"shared_summary": {"$exists": True}})

        # Calculate average group size
        pipeline = [
            {"$group": {"_id": None, "avg_size": {"$avg": "$article_count"}}}
        ]
        avg_size_result = await topics_collection.aggregate(pipeline).to_list(1)
        avg_group_size = avg_size_result[0]["avg_size"] if avg_size_result else 0

        return {
            "articles": {
                "total": total_articles,
                "with_embeddings": articles_with_embeddings,
                "embedding_coverage": (articles_with_embeddings / total_articles * 100) if total_articles > 0 else 0
            },
            "topic_groups": {
                "total": total_topic_groups,
                "with_summaries": topic_groups_with_summaries,
                "summary_coverage": (topic_groups_with_summaries / total_topic_groups * 100) if total_topic_groups > 0 else 0,
                "average_size": round(avg_group_size, 2)
            }
        }

    except Exception as e:
        logger.error(f"Error getting topic analysis stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

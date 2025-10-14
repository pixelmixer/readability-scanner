"""
API routes for daily topics management.
"""

import logging
from typing import List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorDatabase

from database.connection import get_database
from celery_app.tasks import regenerate_daily_topics_task

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/daily-topics", tags=["daily-topics"])


class TopicGroup(BaseModel):
    """Model for a topic group."""
    topic_id: str
    topic_headline: str | None
    date_generated: str
    article_count: int
    combined_summary: str | None
    combined_summary_status: str
    articles: List[Dict[str, Any]]
    created_at: str


class DailyTopicsResponse(BaseModel):
    """Response model for daily topics."""
    success: bool
    topic_groups: List[TopicGroup]
    count: int
    date: str
    generated_at: str | None


class RegenerateResponse(BaseModel):
    """Response model for regeneration request."""
    success: bool
    task_id: str
    message: str


@router.get("/today", response_model=DailyTopicsResponse)
async def get_todays_topics(db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Get today's topic groups.

    Returns pre-computed topic groups from the daily_topics collection.
    These are updated hourly by the Celery worker.
    """
    try:
        topics_collection = db["daily_topics"]

        # Get all topic groups, sorted by article count (most articles first)
        cursor = topics_collection.find({}).sort("article_count", -1)
        topic_docs = await cursor.to_list(length=None)

        logger.info(f"Found {len(topic_docs)} topic groups")

        topic_groups = []
        most_recent_generated_at = None

        for doc in topic_docs:
            # Track the most recent generation time
            date_generated = doc.get('date_generated')
            if date_generated:
                if most_recent_generated_at is None or date_generated > most_recent_generated_at:
                    most_recent_generated_at = date_generated

            topic_groups.append(TopicGroup(
                topic_id=doc['topic_id'],
                topic_headline=doc.get('topic_headline'),
                date_generated=doc['date_generated'].isoformat() if isinstance(doc['date_generated'], datetime) else doc['date_generated'],
                article_count=doc['article_count'],
                combined_summary=doc.get('combined_summary'),
                combined_summary_status=doc.get('combined_summary_status', 'unknown'),
                articles=doc.get('articles', []),
                created_at=doc['created_at'].isoformat() if isinstance(doc['created_at'], datetime) else doc['created_at']
            ))

        return DailyTopicsResponse(
            success=True,
            topic_groups=topic_groups,
            count=len(topic_groups),
            date=datetime.now().strftime("%Y-%m-%d"),
            generated_at=most_recent_generated_at.isoformat() if most_recent_generated_at and isinstance(most_recent_generated_at, datetime) else None
        )

    except Exception as e:
        logger.error(f"Error getting today's topics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/regenerate", response_model=RegenerateResponse)
async def regenerate_topics():
    """
    Manually trigger regeneration of daily topics.

    This will queue a high-priority task to regenerate all topic groups.
    """
    try:
        # Queue the regeneration task
        result = regenerate_daily_topics_task.apply_async(queue='high', priority=10)

        logger.info(f"Daily topics regeneration queued with task ID: {result.id}")

        return RegenerateResponse(
            success=True,
            task_id=result.id,
            message="Daily topics regeneration has been queued. This may take a few minutes."
        )

    except Exception as e:
        logger.error(f"Error triggering daily topics regeneration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_daily_topics_stats(db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Get statistics about daily topics.
    """
    try:
        topics_collection = db["daily_topics"]

        # Count total topic groups
        total_topics = await topics_collection.count_documents({})

        # Count topics with successful combined summaries
        topics_with_summaries = await topics_collection.count_documents({
            "combined_summary_status": "completed"
        })

        # Get total article count
        pipeline = [
            {"$group": {
                "_id": None,
                "total_articles": {"$sum": "$article_count"},
                "avg_articles_per_topic": {"$avg": "$article_count"}
            }}
        ]

        agg_result = await topics_collection.aggregate(pipeline).to_list(1)

        total_articles = agg_result[0]['total_articles'] if agg_result else 0
        avg_articles = agg_result[0]['avg_articles_per_topic'] if agg_result else 0

        # Get most recent generation time
        recent_doc = await topics_collection.find_one(
            {},
            sort=[("date_generated", -1)]
        )

        last_generated = recent_doc['date_generated'] if recent_doc else None

        return {
            "success": True,
            "total_topic_groups": total_topics,
            "topics_with_summaries": topics_with_summaries,
            "total_articles_grouped": total_articles,
            "avg_articles_per_topic": round(avg_articles, 2),
            "last_generated": last_generated.isoformat() if last_generated and isinstance(last_generated, datetime) else None
        }

    except Exception as e:
        logger.error(f"Error getting daily topics stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/diagnostic")
async def diagnostic_check(db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Diagnostic endpoint to check article readiness for topic grouping.
    """
    try:
        from datetime import timedelta

        articles_collection = db["documents"]

        cutoff_date = datetime.now() - timedelta(days=7)

        # Count articles by criteria
        total_articles = await articles_collection.count_documents({})

        articles_with_dates = await articles_collection.count_documents({
            "publication_date": {"$gte": cutoff_date, "$type": "date"}
        })

        articles_with_summaries = await articles_collection.count_documents({
            "publication_date": {"$gte": cutoff_date, "$type": "date"},
            "summary": {"$exists": True, "$ne": None, "$ne": ""},
            "summary_processing_status": "completed"
        })

        articles_with_embeddings = await articles_collection.count_documents({
            "publication_date": {"$gte": cutoff_date, "$type": "date"},
            "summary": {"$exists": True, "$ne": None, "$ne": ""},
            "summary_processing_status": "completed",
            "embedding": {"$exists": True}
        })

        # Sample embedding dimensions
        sample_doc = await articles_collection.find_one({
            "embedding": {"$exists": True}
        })

        embedding_dimension = len(sample_doc.get('embedding', [])) if sample_doc else 0
        embedding_model = sample_doc.get('embedding_model', 'unknown') if sample_doc else 'unknown'

        # Check for multiple embedding dimensions (problematic)
        pipeline = [
            {"$match": {"embedding": {"$exists": True}}},
            {"$project": {
                "embedding_size": {"$size": "$embedding"},
                "embedding_model": 1
            }},
            {"$group": {
                "_id": "$embedding_size",
                "count": {"$sum": 1},
                "models": {"$addToSet": "$embedding_model"}
            }}
        ]

        dimension_counts = await articles_collection.aggregate(pipeline).to_list(10)

        return {
            "success": True,
            "total_articles": total_articles,
            "articles_last_7_days": articles_with_dates,
            "articles_with_summaries": articles_with_summaries,
            "articles_ready_for_grouping": articles_with_embeddings,
            "sample_embedding_dimension": embedding_dimension,
            "sample_embedding_model": embedding_model,
            "embedding_dimensions": dimension_counts,
            "recommendation": _get_recommendation(articles_with_embeddings, dimension_counts)
        }

    except Exception as e:
        logger.error(f"Error in diagnostic check: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _get_recommendation(ready_articles: int, dimension_counts: List[Dict]) -> str:
    """Generate recommendation based on diagnostic results."""
    if ready_articles == 0:
        return "No articles ready for grouping. Ensure articles have publication_date, summary, and embedding."

    if len(dimension_counts) > 1:
        return f"WARNING: Multiple embedding dimensions detected ({len(dimension_counts)} different sizes). This will prevent proper grouping. You may need to regenerate embeddings with a consistent model."

    if ready_articles < 10:
        return f"Only {ready_articles} articles ready. Topic grouping works best with 50+ articles."

    return f"{ready_articles} articles ready for grouping. Try lowering similarity threshold to 0.6 or 0.55 if no groups are created."


"""
API routes for topic analysis management and monitoring.
"""

import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from celery_app.tasks import (
    batch_generate_embeddings,
    group_articles_by_topics,
    generate_shared_summaries,
    full_topic_analysis_pipeline,
    batch_generate_summary_embeddings_task
)
from database.connection import get_database
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/topic-management", tags=["topic-management"])


class TaskResponse(BaseModel):
    """Response model for task operations."""
    success: bool
    task_id: str
    message: str


class StatsResponse(BaseModel):
    """Response model for statistics."""
    articles: Dict[str, Any]
    topic_groups: Dict[str, Any]
    embeddings: Dict[str, Any]


@router.post("/generate-embeddings", response_model=TaskResponse)
async def trigger_embedding_generation(
    batch_size: int = 100,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Trigger embedding generation for articles that don't have them.

    Args:
        batch_size: Number of articles to process in each batch
        db: Database connection

    Returns:
        Task information
    """
    try:
        # Check current status
        collection = db["documents"]
        total_articles = await collection.count_documents({})
        articles_with_embeddings = await collection.count_documents({"embedding": {"$exists": True}})

        if articles_with_embeddings >= total_articles:
            return TaskResponse(
                success=True,
                task_id="none",
                message=f"All {total_articles} articles already have embeddings"
            )

        # Queue the task
        result = batch_generate_embeddings.delay(batch_size)

        return TaskResponse(
            success=True,
            task_id=result.id,
            message=f"Embedding generation queued for {total_articles - articles_with_embeddings} articles"
        )

    except Exception as e:
        logger.error(f"Error triggering embedding generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-summary-embeddings", response_model=TaskResponse)
async def trigger_summary_embedding_generation(
    batch_size: int = 50,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Trigger summary embedding generation for articles that have summaries but no summary embeddings.

    Args:
        batch_size: Number of articles to process in each batch
        db: Database connection

    Returns:
        Task information
    """
    try:
        # Check current status
        collection = db["documents"]
        articles_with_summaries = await collection.count_documents({
            "summary": {"$exists": True, "$ne": None, "$ne": ""},
            "summary_processing_status": "completed"
        })
        articles_with_summary_embeddings = await collection.count_documents({"summary_embedding": {"$exists": True}})

        if articles_with_summary_embeddings >= articles_with_summaries:
            return TaskResponse(
                success=True,
                task_id="none",
                message=f"All {articles_with_summaries} articles with summaries already have summary embeddings"
            )

        # Queue the task
        result = batch_generate_summary_embeddings_task.apply_async(
            args=[batch_size],
            queue='normal'
        )

        return TaskResponse(
            success=True,
            task_id=result.id,
            message=f"Summary embedding generation queued for {articles_with_summaries - articles_with_summary_embeddings} articles"
        )

    except Exception as e:
        logger.error(f"Error triggering summary embedding generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/group-topics", response_model=TaskResponse)
async def trigger_topic_grouping(
    similarity_threshold: float = 0.75,
    min_group_size: int = 2,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Trigger topic grouping for articles with embeddings.

    Args:
        similarity_threshold: Minimum similarity score for grouping
        min_group_size: Minimum number of articles in a topic group
        db: Database connection

    Returns:
        Task information
    """
    try:
        # Check if we have articles with embeddings
        collection = db["documents"]
        articles_with_embeddings = await collection.count_documents({"embedding": {"$exists": True}})

        if articles_with_embeddings == 0:
            raise HTTPException(
                status_code=400,
                detail="No articles with embeddings found. Run embedding generation first."
            )

        # Queue the task
        result = group_articles_by_topics.delay(similarity_threshold, min_group_size)

        return TaskResponse(
            success=True,
            task_id=result.id,
            message=f"Topic grouping queued for {articles_with_embeddings} articles"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering topic grouping: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-summaries", response_model=TaskResponse)
async def trigger_summary_generation(db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Trigger shared summary generation for all topic groups.

    Args:
        db: Database connection

    Returns:
        Task information
    """
    try:
        # Check if we have topic groups
        topics_collection = db["article_topics"]
        total_topics = await topics_collection.count_documents({})

        if total_topics == 0:
            raise HTTPException(
                status_code=400,
                detail="No topic groups found. Run topic grouping first."
            )

        # Queue the task
        result = generate_shared_summaries.delay()

        return TaskResponse(
            success=True,
            task_id=result.id,
            message=f"Summary generation queued for {total_topics} topic groups"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering summary generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-full-pipeline", response_model=TaskResponse)
async def trigger_full_pipeline():
    """
    Trigger the complete topic analysis pipeline.

    Returns:
        Task information
    """
    try:
        # Queue the full pipeline task
        result = full_topic_analysis_pipeline.delay()

        return TaskResponse(
            success=True,
            task_id=result.id,
            message="Full topic analysis pipeline queued"
        )

    except Exception as e:
        logger.error(f"Error triggering full pipeline: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/summary-embeddings")
async def debug_summary_embeddings(db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Debug endpoint to check summary embedding status.

    Returns:
        Detailed information about summary embeddings
    """
    try:
        collection = db["documents"]

        # Get counts
        total_articles = await collection.count_documents({})
        articles_with_summaries = await collection.count_documents({
            "summary": {"$exists": True, "$ne": None, "$ne": ""},
            "summary_processing_status": "completed"
        })
        articles_with_summary_embeddings = await collection.count_documents({
            "summary_embedding": {"$exists": True}
        })
        articles_with_content_embeddings = await collection.count_documents({
            "embedding": {"$exists": True}
        })
        articles_needing_summary_embeddings = await collection.count_documents({
            "summary": {"$exists": True, "$ne": None, "$ne": ""},
            "summary_processing_status": "completed",
            "summary_embedding": {"$exists": False}
        })

        # Get sample with summary embedding
        sample_with_embedding = None
        if articles_with_summary_embeddings > 0:
            doc = await collection.find_one(
                {"summary_embedding": {"$exists": True}},
                {"url": 1, "title": 1, "summary": 1, "summary_embedding": 1}
            )
            if doc:
                sample_with_embedding = {
                    "url": doc.get("url"),
                    "title": doc.get("title", "")[:100],
                    "summary_length": len(doc.get("summary", "")),
                    "embedding_dimensions": len(doc.get("summary_embedding", []))
                }

        # Get sample needing embedding
        sample_needing_embedding = None
        if articles_needing_summary_embeddings > 0:
            doc = await collection.find_one(
                {
                    "summary": {"$exists": True, "$ne": None, "$ne": ""},
                    "summary_processing_status": "completed",
                    "summary_embedding": {"$exists": False}
                },
                {"url": 1, "title": 1, "summary": 1}
            )
            if doc:
                sample_needing_embedding = {
                    "url": doc.get("url"),
                    "title": doc.get("title", "")[:100],
                    "summary_preview": doc.get("summary", "")[:100]
                }

        return {
            "total_articles": total_articles,
            "articles_with_summaries": articles_with_summaries,
            "articles_with_summary_embeddings": articles_with_summary_embeddings,
            "articles_with_content_embeddings": articles_with_content_embeddings,
            "articles_needing_summary_embeddings": articles_needing_summary_embeddings,
            "sample_with_embedding": sample_with_embedding,
            "sample_needing_embedding": sample_needing_embedding
        }

    except Exception as e:
        logger.error(f"Error in debug endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=StatsResponse)
async def get_topic_analysis_stats(db: AsyncIOMotorDatabase = Depends(get_database)):
    """
    Get comprehensive topic analysis statistics.

    Args:
        db: Database connection

    Returns:
        Detailed statistics
    """
    try:
        # Get article statistics
        collection = db["documents"]
        total_articles = await collection.count_documents({})
        articles_with_embeddings = await collection.count_documents({"embedding": {"$exists": True}})

        # Get embedding statistics
        embedding_stats = await collection.aggregate([
            {"$match": {"embedding": {"$exists": True}}},
            {"$group": {
                "_id": "$embedding_model",
                "count": {"$sum": 1}
            }}
        ]).to_list(length=None)

        # Get topic group statistics
        topics_collection = db["article_topics"]
        total_topic_groups = await topics_collection.count_documents({})
        topic_groups_with_summaries = await topics_collection.count_documents({"shared_summary": {"$exists": True}})

        # Calculate average group size
        avg_size_result = await topics_collection.aggregate([
            {"$group": {"_id": None, "avg_size": {"$avg": "$article_count"}}}
        ]).to_list(1)
        avg_group_size = avg_size_result[0]["avg_size"] if avg_size_result else 0

        # Get recent activity
        recent_topics = await topics_collection.find(
            {},
            {"created_at": 1, "article_count": 1}
        ).sort("created_at", -1).limit(5).to_list(length=5)

        return StatsResponse(
            articles={
                "total": total_articles,
                "with_embeddings": articles_with_embeddings,
                "embedding_coverage": (articles_with_embeddings / total_articles * 100) if total_articles > 0 else 0
            },
            topic_groups={
                "total": total_topic_groups,
                "with_summaries": topic_groups_with_summaries,
                "summary_coverage": (topic_groups_with_summaries / total_topic_groups * 100) if total_topic_groups > 0 else 0,
                "average_size": round(avg_group_size, 2),
                "recent_groups": [
                    {
                        "created_at": topic["created_at"].isoformat(),
                        "article_count": topic["article_count"]
                    }
                    for topic in recent_topics
                ]
            },
            embeddings={
                "models": {stat["_id"]: stat["count"] for stat in embedding_stats},
                "total_embeddings": articles_with_embeddings
            }
        )

    except Exception as e:
        logger.error(f"Error getting topic analysis stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/scheduler-status")
async def get_scheduler_status():
    """
    Get topic analysis scheduler status.

    Returns:
        Scheduler status information
    """
    try:
        from scheduler.topic_scheduler import topic_scheduler

        status = topic_scheduler.get_status()
        return status

    except Exception as e:
        logger.error(f"Error getting scheduler status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup-old-topics")
async def cleanup_old_topics(
    days_old: int = 30,
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Cleanup topic groups older than specified days.

    Args:
        days_old: Delete topic groups older than this many days
        db: Database connection

    Returns:
        Cleanup results
    """
    try:
        from datetime import datetime, timedelta

        topics_collection = db["article_topics"]
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        # Count topics to be deleted
        count_result = await topics_collection.count_documents({
            "created_at": {"$lt": cutoff_date}
        })

        if count_result == 0:
            return {
                "success": True,
                "message": f"No topic groups older than {days_old} days found",
                "deleted_count": 0
            }

        # Delete old topics
        result = await topics_collection.delete_many({
            "created_at": {"$lt": cutoff_date}
        })

        return {
            "success": True,
            "message": f"Cleaned up {result.deleted_count} topic groups older than {days_old} days",
            "deleted_count": result.deleted_count
        }

    except Exception as e:
        logger.error(f"Error cleaning up old topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

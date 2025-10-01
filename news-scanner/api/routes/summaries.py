"""
Summary management API routes.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks, Form
from pydantic import BaseModel, HttpUrl

from database.articles import article_repository
from database.connection import db_manager
from celery_app.tasks import (
    manual_summary_trigger_task,
    backfill_publication_dates_task,
    generate_article_summary_task,
    process_summary_backlog_task,
    scheduled_scan_trigger_task
)
from celery_app.queue_manager import queue_manager

logger = logging.getLogger(__name__)

router = APIRouter()


class SummaryStatsResponse(BaseModel):
    """Response model for summary statistics."""
    total_articles: int
    status_breakdown: Dict[str, int]
    summary_coverage: float
    articles_without_summaries: int


@router.get("/stats", response_model=SummaryStatsResponse)
async def get_summary_statistics():
    """Get summary processing statistics."""
    try:
        # Ensure database connection
        if not db_manager._connected:
            await db_manager.connect()

        # Get summary statistics
        stats = await article_repository.get_summary_statistics()

        # Get count of articles without summaries
        articles_without_summaries = await article_repository.count_articles_without_summaries()

        return SummaryStatsResponse(
            total_articles=stats["total_articles"],
            status_breakdown=stats["status_breakdown"],
            summary_coverage=stats["summary_coverage"],
            articles_without_summaries=articles_without_summaries
        )

    except Exception as e:
        logger.error(f"Error getting summary statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger")
async def trigger_summary_generation(batch_size: int = Form(50)):
    """Manually trigger summary generation for articles."""
    try:
        # Ensure database connection
        if not db_manager._connected:
            await db_manager.connect()

        # Get current statistics
        stats = await article_repository.get_summary_statistics()

        # Trigger summary processing
        task_result = manual_summary_trigger_task.apply_async(
            args=[batch_size],
            queue='normal',
            priority=5
        )

        return {
            "success": True,
            "message": f"Summary generation triggered for up to {batch_size} articles",
            "task_id": task_result.id,
            "current_stats": stats,
            "batch_size": batch_size
        }

    except Exception as e:
        logger.error(f"Error triggering summary generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger/{article_url:path}")
async def trigger_single_article_summary(article_url: str):
    """Trigger summary generation for a specific article."""
    try:
        # Ensure database connection
        if not db_manager._connected:
            await db_manager.connect()

        # Check if article exists
        article = await article_repository.get_article_by_url(article_url)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")

        # Trigger summary generation
        task_result = generate_article_summary_task.apply_async(
            args=[article_url],
            queue='normal',
            priority=4
        )

        return {
            "success": True,
            "message": f"Summary generation triggered for article",
            "task_id": task_result.id,
            "article_url": article_url,
            "article_title": article.title
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering single article summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queue/status")
async def get_summary_queue_status():
    """Get current summary processing queue status."""
    try:
        # Get general queue stats
        queue_stats = await queue_manager.get_queue_stats()

        # Get summary-specific statistics
        if not db_manager._connected:
            await db_manager.connect()

        summary_stats = await article_repository.get_summary_statistics()

        return {
            "success": True,
            "queue_stats": queue_stats,
            "summary_stats": summary_stats,
            "timestamp": "2024-01-15T10:30:00Z"  # You might want to use actual timestamp
        }

    except Exception as e:
        logger.error(f"Error getting summary queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/articles/without-summaries")
async def get_articles_without_summaries(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0)
):
    """Get articles that don't have summaries yet."""
    try:
        # Ensure database connection
        if not db_manager._connected:
            await db_manager.connect()

        articles = await article_repository.get_articles_without_summaries(limit=limit, skip=skip)

        # Convert to response format
        article_list = []
        for article in articles:
            article_list.append({
                "url": str(article.url),
                "title": article.title,
                "origin": article.origin,
                "publication_date": article.publication_date,
                "summary_status": article.summary_processing_status or "no_summary",
                "summary_error": article.summary_error
            })

        return {
            "success": True,
            "articles": article_list,
            "count": len(article_list),
            "limit": limit,
            "skip": skip
        }

    except Exception as e:
        logger.error(f"Error getting articles without summaries: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/articles/today")
async def get_todays_articles(limit: int = Query(100, ge=1, le=500)):
    """Get today's articles for newspaper layout."""
    try:
        # Ensure database connection
        if not db_manager._connected:
            await db_manager.connect()

        articles = await article_repository.get_todays_articles(limit=limit)

        # Convert to response format
        article_list = []
        for article in articles:
            article_list.append({
                "url": str(article.url),
                "title": article.title,
                "origin": article.origin,
                "publication_date": article.publication_date,
                "summary": article.summary,
                "content": article.content,
                "cleaned_data": article.cleaned_data,
                "summary_generated_at": article.summary_generated_at,
                "summary_model": article.summary_model
            })

        return {
            "success": True,
            "articles": article_list,
            "count": len(article_list),
            "date": datetime.now().strftime("%Y-%m-%d")
        }

    except Exception as e:
        logger.error(f"Error getting today's articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/articles/{article_url:path}")
async def get_article_with_summary(article_url: str):
    """Get a specific article with its summary information."""
    try:
        # Ensure database connection
        if not db_manager._connected:
            await db_manager.connect()

        article = await article_repository.get_article_by_url(article_url)
        if not article:
            raise HTTPException(status_code=404, detail="Article not found")

        return {
            "success": True,
            "article": {
                "url": str(article.url),
                "title": article.title,
                "content": article.content,
                "cleaned_data": article.cleaned_data,
                "origin": article.origin,
                "publication_date": article.publication_date,
                "summary": article.summary,
                "summary_generated_at": article.summary_generated_at,
                "summary_model": article.summary_model,
                "summary_prompt_version": article.summary_prompt_version,
                "summary_processing_status": article.summary_processing_status,
                "summary_error": article.summary_error,
                "readability_metrics": {
                    "words": article.words,
                    "sentences": article.sentences,
                    "flesch": article.flesch,
                    "flesch_kincaid": article.flesch_kincaid,
                    "smog": article.smog,
                    "gunning_fog": article.gunning_fog
                }
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting article with summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/backfill-dates")
async def trigger_publication_date_backfill(batch_size: int = Form(20)):
    """Manually trigger publication date backfill for articles missing dates."""
    try:
        # Ensure database connection
        if not db_manager._connected:
            await db_manager.connect()

        # Get current statistics
        total_without_dates = await article_repository.count_articles_without_publication_date()
        total_articles = await article_repository.count_articles()

        # Trigger backfill processing
        task_result = backfill_publication_dates_task.apply_async(
            args=[batch_size],
            queue='normal',
            priority=5
        )

        return {
            "success": True,
            "message": f"Publication date backfill triggered for up to {batch_size} articles",
            "task_id": task_result.id,
            "total_articles": total_articles,
            "articles_without_dates": total_without_dates,
            "batch_size": batch_size
        }

    except Exception as e:
        logger.error(f"Error triggering publication date backfill: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/date-stats")
async def get_publication_date_statistics():
    """Get statistics about publication dates in the database."""
    try:
        # Ensure database connection
        if not db_manager._connected:
            await db_manager.connect()

        total_articles = await article_repository.count_articles()
        articles_without_dates = await article_repository.count_articles_without_publication_date()
        articles_with_dates = total_articles - articles_without_dates

        coverage_percentage = (articles_with_dates / total_articles * 100) if total_articles > 0 else 0

        return {
            "success": True,
            "total_articles": total_articles,
            "articles_with_dates": articles_with_dates,
            "articles_without_dates": articles_without_dates,
            "date_coverage": round(coverage_percentage, 1)
        }

    except Exception as e:
        logger.error(f"Error getting publication date statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/trigger-scan")
async def trigger_manual_scan():
    """Manually trigger RSS source scanning."""
    try:
        # Trigger scheduled scan task
        task_result = scheduled_scan_trigger_task.apply_async(
            queue='low',
            priority=3
        )

        return {
            "success": True,
            "message": "RSS source scanning triggered",
            "task_id": task_result.id,
            "job_type": "rss_scan"
        }

    except Exception as e:
        logger.error(f"Error triggering RSS scan: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/trigger-backlog")
async def trigger_backlog_processing(batch_size: int = Form(10)):
    """Manually trigger summary backlog processing."""
    try:
        # Trigger backlog processing
        task_result = process_summary_backlog_task.apply_async(
            args=[batch_size],
            queue='low',
            priority=2
        )

        return {
            "success": True,
            "message": f"Summary backlog processing triggered (batch size: {batch_size})",
            "task_id": task_result.id,
            "job_type": "summary_backlog",
            "batch_size": batch_size
        }

    except Exception as e:
        logger.error(f"Error triggering backlog processing: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/status/{task_id}")
async def get_job_status(task_id: str):
    """Get the status of a specific job."""
    try:
        from celery_app.celery_worker import celery_app

        # Get task result
        result = celery_app.AsyncResult(task_id)

        if result.state == 'PENDING':
            response = {
                'state': result.state,
                'status': 'Task is waiting to be processed...'
            }
        elif result.state == 'PROGRESS':
            response = {
                'state': result.state,
                'current': result.info.get('current', 0),
                'total': result.info.get('total', 1),
                'status': result.info.get('status', '')
            }
        elif result.state == 'SUCCESS':
            response = {
                'state': result.state,
                'result': result.result,
                'status': 'Task completed successfully'
            }
        else:  # FAILURE or other states
            response = {
                'state': result.state,
                'status': str(result.info),
                'error': str(result.info) if result.state == 'FAILURE' else None
            }

        return {
            "success": True,
            "task_id": task_id,
            "status": response
        }

    except Exception as e:
        logger.error(f"Error getting job status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/queue-status")
async def get_queue_status():
    """Get current queue status and statistics."""
    try:
        from celery_app.celery_worker import celery_app

        # Get queue statistics
        inspect = celery_app.control.inspect()

        # Get active tasks
        active_tasks = inspect.active()

        # Get scheduled tasks
        scheduled_tasks = inspect.scheduled()

        # Get reserved tasks
        reserved_tasks = inspect.reserved()

        # Count tasks by queue
        queue_stats = {}
        total_active = 0
        total_scheduled = 0
        total_reserved = 0

        if active_tasks:
            for worker, tasks in active_tasks.items():
                queue_name = worker.split('@')[0] if '@' in worker else 'default'
                queue_stats[queue_name] = queue_stats.get(queue_name, 0) + len(tasks)
                total_active += len(tasks)

        if scheduled_tasks:
            for worker, tasks in scheduled_tasks.items():
                total_scheduled += len(tasks)

        if reserved_tasks:
            for worker, tasks in reserved_tasks.items():
                total_reserved += len(tasks)

        return {
            "success": True,
            "queue_stats": queue_stats,
            "total_active": total_active,
            "total_scheduled": total_scheduled,
            "total_reserved": total_reserved,
            "workers": list(active_tasks.keys()) if active_tasks else []
        }

    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


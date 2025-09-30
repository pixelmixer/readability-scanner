"""
RSS source management routes.
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from models.source import Source, SourceCreate, SourceUpdate
from database.sources import source_repository
from scanner.rss_parser import rss_parser
from scanner.scanner import scan_single_source
from api.dependencies import get_database, get_templates, get_settings
from celery_app.queue_manager import queue_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def sources_page(
    request: Request,
    templates: Jinja2Templates = Depends(get_templates),
    settings = Depends(get_settings)
):
    """Display the sources management page."""
    try:
        # Get all sources with statistics
        sources_with_stats = await source_repository.get_sources_with_stats()

        return templates.TemplateResponse("pages/sources.html", {
            "request": request,
            "sources": sources_with_stats,
            "title": "News Sources Management",
            "buildTimestamp": settings.build_timestamp,
            "buildVersion": settings.build_version
        })

    except Exception as e:
        logger.error(f"Error fetching sources page: {e}")
        raise HTTPException(status_code=500, detail="Error fetching sources")


@router.get("/api", response_model=List[dict])
async def get_sources_api():
    """Get all sources as JSON API."""
    try:
        return await source_repository.get_sources_with_stats()
    except Exception as e:
        logger.error(f"Error fetching sources API: {e}")
        raise HTTPException(status_code=500, detail="Error fetching sources")


@router.post("/preview")
async def preview_rss_feed(url: str = Form(...)):
    """Preview an RSS feed to get title and basic info."""
    try:
        # Validate URL format
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(status_code=400, detail="Invalid URL format")

        # Use RSS parser to get feed info
        from scanner.rss_parser import rss_parser
        title = rss_parser.get_feed_title(url)

        if title:
            return {"success": True, "title": title, "url": url}
        else:
            return {"success": False, "error": "Could not fetch feed title"}

    except Exception as e:
        logger.error(f"Error previewing RSS feed {url}: {e}")
        return {"success": False, "error": str(e)}


@router.post("/add")
async def add_source(
    request: Request,
    url: str = Form(...),
    name: str = Form(""),
    description: str = Form("")
):
    """Add a new RSS source."""
    try:
        # Validate required fields
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")

        # Validate URL format
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid URL format")

        # Check for API endpoints
        url_lower = url.lower()
        is_likely_api = any(indicator in url_lower for indicator in [
            '/api/', 'json', '.json', 'format=json'
        ])

        if is_likely_api:
            raise HTTPException(
                status_code=400,
                detail="This appears to be an API endpoint, not an RSS feed. Please use an RSS feed URL."
            )

        # Validate RSS feed
        try:
            logger.info(f"Validating RSS feed: {url}")
            if not rss_parser.validate_feed_url(url):
                raise HTTPException(
                    status_code=400,
                    detail="Unable to parse this URL as an RSS feed. Please verify it's a valid RSS/XML feed."
                )
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            logger.error(f"RSS validation failed for {url}: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"RSS feed validation failed: {e}. Please check that this is a valid RSS feed URL."
            )

        # Create source
        source_data = SourceCreate(
            url=url,
            name=name or urlparse(url).hostname,
            description=description
        )

        new_source = await source_repository.create_source(source_data)
        if not new_source:
            raise HTTPException(status_code=500, detail="Failed to create source")

        logger.info(f"Added new RSS source: {url}")

        # Queue immediate scan with normal priority
        queue_result = await queue_manager.queue_source_scan(url, priority=7)
        if queue_result['success']:
            logger.info(f"📤 Immediate scan queued for new source: {name} (Task ID: {queue_result['task_id']})")
        else:
            logger.warning(f"⚠️ Failed to queue immediate scan for new source: {name}")

        # Redirect back to sources page
        return RedirectResponse(url="/sources", status_code=302)

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error adding source: {e}")
        raise HTTPException(status_code=500, detail="Error adding source")


@router.post("/edit/{source_id}")
async def edit_source(
    source_id: str,
    url: str = Form(...),
    name: str = Form(""),
    description: str = Form("")
):
    """Edit an existing RSS source."""
    try:
        if not url:
            raise HTTPException(status_code=400, detail="URL is required")

        # Validate URL format
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid URL format")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid URL format")

        # Get old source to check for URL changes
        old_source = await source_repository.get_source_by_id(source_id)
        url_changed = old_source and str(old_source.url) != url

        # Update source
        update_data = SourceUpdate(
            url=url,
            name=name or urlparse(url).hostname,
            description=description
        )

        updated_source = await source_repository.update_source(source_id, update_data)
        if not updated_source:
            raise HTTPException(status_code=404, detail="Source not found")

        logger.info(f"Updated RSS source: {source_id}")

        # Queue immediate scan if URL changed
        if url_changed:
            queue_result = await queue_manager.queue_source_scan(url, priority=7)
            if queue_result['success']:
                logger.info(f"📤 Immediate scan queued for updated source: {name} (Task ID: {queue_result['task_id']})")
            else:
                logger.warning(f"⚠️ Failed to queue immediate scan for updated source: {name}")

        return RedirectResponse(url="/sources", status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error editing source: {e}")
        raise HTTPException(status_code=500, detail="Error editing source")


@router.post("/delete/{source_id}")
async def delete_source(source_id: str):
    """Delete an RSS source."""
    try:
        success = await source_repository.delete_source(source_id)
        if not success:
            raise HTTPException(status_code=404, detail="Source not found")

        logger.info(f"Deleted RSS source: {source_id}")
        return RedirectResponse(url="/sources", status_code=302)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting source: {e}")
        raise HTTPException(status_code=500, detail="Error deleting source")


@router.post("/refresh/{source_id}")
async def refresh_source(source_id: str, wait_for_result: bool = True):
    """
    Manually refresh/scan an RSS source using high-priority queue.

    Args:
        source_id: Database ID of the source
        wait_for_result: If True, wait for task completion (default)
    """
    try:
        # Get the source
        source = await source_repository.get_source_by_id(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        logger.info(f"🔄 Manual refresh queued for source: {source.name} ({source.url})")

        # Queue the manual refresh task with high priority
        queue_result = await queue_manager.queue_manual_refresh(
            source_id=source_id,
            source_url=str(source.url),
            wait_for_result=wait_for_result,
            timeout=300  # 5 minute timeout
        )

        if not queue_result['success']:
            logger.error(f"❌ Failed to queue manual refresh for {source.name}: {queue_result.get('error')}")
            raise HTTPException(status_code=500, detail=queue_result.get('error', 'Failed to queue refresh'))

        # Update last refreshed timestamp
        await source_repository.update_last_refreshed(source_id)

        if wait_for_result:
            # Return the task result
            if queue_result.get('completed') and queue_result.get('result', {}).get('success'):
                task_result = queue_result['result']
                logger.info(f"✅ Manual refresh completed for {source.name}")

                return {
                    "success": True,
                    "task_id": queue_result['task_id'],
                    "result": {
                        "scanned": task_result.get('scanned', 0),
                        "total": task_result.get('total', 0),
                        "failed": task_result.get('failed', 0),
                        "failure_rate": task_result.get('failure_rate', 0),
                        "source": source.name,
                        "url": str(source.url)
                    }
                }
            else:
                # Task failed or timed out
                error_msg = queue_result.get('error', 'Refresh task failed or timed out')
                logger.error(f"❌ Manual refresh failed for {source.name}: {error_msg}")
                return {
                    "success": False,
                    "task_id": queue_result.get('task_id'),
                    "error": error_msg,
                    "source": source.name
                }
        else:
            # Return immediately with task ID
            return {
                "success": True,
                "task_id": queue_result['task_id'],
                "status": "queued",
                "message": f"Refresh queued for {source.name}",
                "source": source.name,
                "url": str(source.url)
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing source: {e}")
        raise HTTPException(status_code=500, detail="Error refreshing source")


# Queue Management Endpoints

@router.get("/queue/status")
async def get_queue_status():
    """Get current queue statistics and worker status."""
    try:
        stats = await queue_manager.get_queue_stats()
        return stats
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        raise HTTPException(status_code=500, detail="Error getting queue status")


@router.get("/queue/task/{task_id}")
async def get_task_status(task_id: str):
    """Get status of a specific task."""
    try:
        status = await queue_manager.get_task_status(task_id)
        return status
    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        raise HTTPException(status_code=500, detail="Error getting task status")


@router.post("/queue/trigger-scan")
async def trigger_scheduled_scan():
    """Manually trigger the scheduled scan for all sources."""
    try:
        result = await queue_manager.trigger_scheduled_scan()
        if result['success']:
            logger.info(f"📤 Scheduled scan triggered (Task ID: {result['task_id']})")
            return {
                "success": True,
                "message": "Scheduled scan triggered successfully",
                "task_id": result['task_id']
            }
        else:
            logger.error(f"❌ Failed to trigger scheduled scan: {result.get('error')}")
            raise HTTPException(status_code=500, detail=result.get('error', 'Failed to trigger scan'))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering scheduled scan: {e}")
        raise HTTPException(status_code=500, detail="Error triggering scheduled scan")


@router.delete("/queue/task/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a pending or running task."""
    try:
        result = await queue_manager.cancel_task(task_id)
        if result['success']:
            logger.info(f"🚫 Task canceled: {task_id}")
            return {
                "success": True,
                "message": f"Task {task_id} canceled successfully"
            }
        else:
            logger.error(f"❌ Failed to cancel task {task_id}: {result.get('error')}")
            return {
                "success": False,
                "error": result.get('error', 'Failed to cancel task')
            }
    except Exception as e:
        logger.error(f"Error canceling task: {e}")
        raise HTTPException(status_code=500, detail="Error canceling task")

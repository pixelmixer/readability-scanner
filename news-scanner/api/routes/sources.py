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

        # Start immediate scan in background
        import asyncio
        asyncio.create_task(scan_new_source_background(url, name))

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

        # Start immediate scan if URL changed
        if url_changed:
            import asyncio
            asyncio.create_task(scan_updated_source_background(url, name, "URL changed"))

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
async def refresh_source(source_id: str):
    """Manually refresh/scan an RSS source."""
    try:
        # Get the source
        source = await source_repository.get_source_by_id(source_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source not found")

        logger.info(f"🔄 Manual refresh triggered for source: {source.name} ({source.url})")

        # Perform scan
        scan_result = await scan_single_source(str(source.url), source.name)

        # Update last refreshed timestamp
        await source_repository.update_last_refreshed(source_id)

        if scan_result.success:
            logger.info(f"✅ Manual refresh completed for {source.name}: {scan_result.stats.scanned}/{scan_result.stats.total} articles processed")

            return {
                "success": True,
                "result": {
                    "scanned": scan_result.stats.scanned,
                    "total": scan_result.stats.total,
                    "failed": scan_result.stats.failed,
                    "source": source.name,
                    "url": str(source.url),
                    "duration": scan_result.duration_seconds
                }
            }
        else:
            logger.error(f"❌ Manual refresh failed for {source.name}: {scan_result.error}")
            return {
                "success": False,
                "error": scan_result.error or "Scan failed",
                "source": source.name
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing source: {e}")
        raise HTTPException(status_code=500, detail="Error refreshing source")


async def scan_new_source_background(url: str, name: str):
    """Background task to scan a newly added source."""
    try:
        logger.info(f"🔍 Starting immediate scan of new source: {name} ({url})")
        scan_result = await scan_single_source(url, name)

        if scan_result.has_high_failure_rate:
            logger.warning(f"⚠️ New source {name} has high failure rate. Consider checking for anti-bot protection.")
        else:
            logger.info(f"✅ Immediate scan completed for new source: {scan_result.stats.scanned}/{scan_result.stats.total} articles processed")

    except Exception as e:
        logger.error(f"Background scan failed for new source {url}: {e}")


async def scan_updated_source_background(url: str, name: str, reason: str):
    """Background task to scan an updated source."""
    try:
        logger.info(f"🔍 Starting immediate scan of updated source ({reason}): {name} ({url})")
        scan_result = await scan_single_source(url, name)

        if scan_result.has_high_failure_rate:
            logger.warning(f"⚠️ Updated source {name} has high failure rate.")
        else:
            logger.info(f"✅ Immediate scan completed for updated source: {scan_result.stats.scanned}/{scan_result.stats.total} articles processed")

    except Exception as e:
        logger.error(f"Background scan failed for updated source {url}: {e}")

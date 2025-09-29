"""
Daily readability reports routes.
"""

import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Query, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from database.articles import article_repository
from api.dependencies import get_templates, get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def daily_report(
    request: Request,
    start: str = Query(None, description="Start date (YYYY-MM-DD format)"),
    end: str = Query(None, description="End date (YYYY-MM-DD format)"),
    format: str = Query("html", description="Response format: html or json"),
    templates: Jinja2Templates = Depends(get_templates),
    settings = Depends(get_settings)
):
    """
    Generate daily readability report.

    This endpoint provides aggregated readability metrics by news source
    for a specified date range.
    """
    try:
        # Parse date parameters
        if end:
            end_date = datetime.strptime(end, "%Y-%m-%d")
        else:
            end_date = datetime.now()

        if start:
            start_date = datetime.strptime(start, "%Y-%m-%d")
        else:
            start_date = end_date - timedelta(days=7)  # Default to 1 week

        # Get aggregated data
        results = await article_repository.aggregate_readability_by_host(
            start_date=start_date,
            end_date=end_date,
            min_articles=1
        )

        # Format dates for display
        formatted_start = start_date.strftime("%m/%d/%y %H:%M")
        formatted_end = end_date.strftime("%m/%d/%y %H:%M")

        # Calculate duration
        diff = end_date - start_date
        duration = diff.days

        # Calculate previous/next periods
        previous_start = start_date - diff
        next_end = end_date + diff

        dates = {
            "formattedStart": formatted_start,
            "formattedEnd": formatted_end,
            "previous": previous_start.strftime("%m/%d/%y %H:%M"),
            "next": next_end.strftime("%m/%d/%y %H:%M"),
            "duration": duration
        }

        if format == "json":
            return results
        else:
            return templates.TemplateResponse("pages/daily.html", {
                "request": request,
                "results": results,
                "dates": dates,
                "title": "Daily News Readability Report",
                "buildTimestamp": settings.build_timestamp,
                "buildVersion": settings.build_version
            })

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error generating daily report: {e}")
        raise HTTPException(status_code=500, detail="Error generating daily report")

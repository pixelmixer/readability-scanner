"""
Graph/chart data routes for readability visualization.
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
async def graph_report(
    request: Request,
    start: str = Query(None, description="Start date"),
    end: str = Query(None, description="End date"),
    days: int = Query(20, description="Number of days to analyze"),
    format: str = Query("html", description="Response format: html or json"),
    templates: Jinja2Templates = Depends(get_templates),
    settings = Depends(get_settings)
):
    """
    Generate graph data for readability trends over time.

    This endpoint provides time-series data for charting readability metrics.
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
            start_date = end_date - timedelta(days=days)

        # TODO: Implement daily aggregation for graph data
        # This would involve creating multiple date buckets and aggregating by day

        # Placeholder response
        graph_data = {
            "days": days,
            "data": []  # This would contain time-series data for each source
        }

        dates = {
            "formattedStart": start_date.strftime("%m/%d/%y %H:%M"),
            "formattedEnd": end_date.strftime("%m/%d/%y %H:%M"),
            "duration": (end_date - start_date).days
        }

        if format == "json":
            return graph_data
        else:
            return templates.TemplateResponse("pages/graph.html", {
                "request": request,
                "results": graph_data,
                "dateList": [],  # List of date labels for x-axis
                "dates": dates,
                "title": "Daily News Readability Report",
                "buildTimestamp": settings.build_timestamp,
                "buildVersion": settings.build_version
            })

    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        logger.error(f"Error generating graph data: {e}")
        raise HTTPException(status_code=500, detail="Error generating graph data")

"""
Data export routes for CSV and JSON downloads.
"""

import logging
import csv
import io
from datetime import datetime
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import StreamingResponse

from database.articles import article_repository

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def export_data(
    type: str = Query("csv", description="Export format: csv or json"),
    min_articles: int = Query(100, description="Minimum articles per source")
):
    """
    Export readability data in CSV or JSON format.

    This endpoint provides aggregated readability metrics for download.
    """
    try:
        # Get aggregated data
        results = await article_repository.aggregate_readability_by_host(
            min_articles=min_articles
        )

        if not results:
            raise HTTPException(status_code=404, detail="No data found matching criteria")

        if type == "json":
            import json
            return results

        elif type == "csv":
            # Convert to CSV
            output = io.StringIO()

            if results:
                # Get field names from first result
                fieldnames = results[0].keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(results)

            output.seek(0)

            # Create streaming response
            def generate():
                yield output.getvalue()

            return StreamingResponse(
                generate(),
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=readability_report.csv"}
            )

        else:
            raise HTTPException(status_code=400, detail="Invalid export type. Use 'csv' or 'json'")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting data: {e}")
        raise HTTPException(status_code=500, detail="Error exporting data")

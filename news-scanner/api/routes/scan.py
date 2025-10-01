"""
Manual scanning routes for testing individual URLs.
"""

import logging
from fastapi import APIRouter, Query, HTTPException
from urllib.parse import urlparse

from scanner.content_extractor import content_extractor, ContentExtractionError
from readability.analyzer import analyzer
from database.articles import article_repository
from datetime import datetime
import aiohttp

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/")
async def scan_url(url: str = Query(..., description="URL to scan and analyze")):
    """
    Scan a single URL for content and perform readability analysis.

    This endpoint mimics the Node.js /scan functionality for testing.
    """
    try:
        logger.info(f"Requested manual scan of: {url}")

        if not url:
            raise HTTPException(
                status_code=400,
                detail="Please include a URL to search: like: ?url=http://example.com/article-name"
            )

        # Validate URL format
        try:
            parsed_url = urlparse(url)
            if not parsed_url.scheme or not parsed_url.netloc:
                raise ValueError("Invalid URL format")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid URL format")

        # Extract content using readability service
        async with aiohttp.ClientSession() as session:
            try:
                content_data = await content_extractor.extract_content(url, session)

                if not content_data.get('content'):
                    raise HTTPException(
                        status_code=404,
                        detail="No content found in the page response"
                    )

                logger.info(f"Successfully extracted content from: {url}")

                # Process and save the response
                processed_content = await process_and_save_response(content_data)

                return {
                    "success": True,
                    "url": url,
                    "content_length": len(content_data.get('content', '')),
                    "cleaned_content_length": len(processed_content),
                    "message": "Article successfully scanned and analyzed",
                    "readability_preview": {
                        "words": content_data.get('words', 0),
                        "flesch": content_data.get('Flesch', 0),
                        "flesch_kincaid": content_data.get('Flesch Kincaid', 0)
                    }
                }

            except ContentExtractionError as e:
                logger.error(f"Content extraction failed for {url}: {e}")

                error_detail = f"Content extraction failed: {e}"
                if e.status_code:
                    error_detail = f"HTTP {e.status_code}: {e}"

                raise HTTPException(
                    status_code=e.status_code or 500,
                    detail=error_detail
                )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Unexpected error scanning {url}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {e}"
        )


async def process_and_save_response(content_data: dict) -> str:
    """
    Process extracted content with readability analysis and save to database.

    This mimics the parseAndSaveResponse function from the Node.js version.
    """
    try:
        url = content_data.get('url')
        content = content_data.get('content', '')

        logger.info(f"Processing and analyzing content from: {url}")

        # Perform readability analysis
        readability_metrics = analyzer.analyze_and_convert_to_dict(content, is_html=True)

        # Clean content for storage
        cleaned_content = analyzer.clean_html_content(content)

        # Merge all data
        from datetime import timezone
        article_data = {
            **content_data,
            **readability_metrics,
            'Cleaned Data': cleaned_content,
            'Host': urlparse(url).hostname if url else None,
            'date': datetime.now(timezone.utc)
        }

        # Save to database
        success = await article_repository.upsert_article(article_data)

        if success:
            logger.info(f"Successfully saved article analysis for: {url}")
        else:
            logger.warning(f"Failed to save article analysis for: {url}")

        return cleaned_content

    except Exception as e:
        logger.error(f"Error processing response: {e}")
        raise


@router.get("/test")
async def test_scan_service():
    """Test endpoint to verify scanning functionality."""
    return {
        "service": "News Scanner API",
        "status": "operational",
        "endpoints": {
            "scan": "/scan?url=<article_url>",
            "sources": "/sources",
            "health": "/health"
        },
        "example": "/scan?url=https://example.com/news-article"
    }

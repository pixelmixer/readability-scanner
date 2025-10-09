"""
Article search routes for free text search functionality.
"""

import logging
import re
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Query, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from database.connection import get_database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/articles", tags=["articles"])


@router.get("/search")
async def search_articles(
    q: str = Query(..., description="Search query"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(25, ge=1, le=100, description="Results per page"),
    db: AsyncIOMotorDatabase = Depends(get_database)
):
    """
    Search articles by free text query.

    Searches through article titles and content using MongoDB text search.
    Falls back to regex search if text index is not available.
    Supports pagination and returns highlighted results.

    Args:
        q: Search query string
        page: Page number (1-based)
        limit: Number of results per page
        db: Database connection

    Returns:
        Dictionary containing search results with pagination info
    """
    try:
        if not q or not q.strip():
            raise HTTPException(status_code=400, detail="Search query cannot be empty")

        collection = db["documents"]
        search_terms = q.strip().split()
        formatted_articles = []

        # Try text search first
        try:
            # Create text search query
            search_query = {
                "$text": {
                    "$search": q,
                    "$caseSensitive": False,
                    "$diacriticSensitive": False
                }
            }

            # Get total count for pagination
            total_count = await collection.count_documents(search_query)

            # Calculate skip value for pagination
            skip = (page - 1) * limit

            # Perform search with text score
            cursor = collection.find(
                search_query,
                {
                    "title": 1,
                    "url": 1,
                    "Host": 1,
                    "publication_date": 1,
                    "Cleaned Data": 1,
                    "content": 1,
                    "readability_score": 1,
                    "score": {"$meta": "textScore"}
                }
            ).sort([("score", {"$meta": "textScore"})]).skip(skip).limit(limit)

            articles = await cursor.to_list(length=limit)

            # Format articles for response
            for article in articles:
                # Generate preview text
                content = article.get('Cleaned Data', '') or article.get('content', '')
                preview = _generate_preview(content)

                formatted_articles.append({
                    "url": article["url"],
                    "title": article.get("title", "Untitled"),
                    "host": article.get("Host", ""),
                    "publication_date": article.get("publication_date"),
                    "preview": preview,
                    "readability_score": article.get("readability_score"),
                    "relevance_score": article.get("score", 0)
                })

        except Exception as text_search_error:
            logger.warning(f"Text search failed, falling back to regex search: {text_search_error}")

            # Fallback to regex search on title and content
            regex_pattern = "|".join(re.escape(term) for term in search_terms)
            search_query = {
                "$or": [
                    {"title": {"$regex": regex_pattern, "$options": "i"}},
                    {"Cleaned Data": {"$regex": regex_pattern, "$options": "i"}},
                    {"content": {"$regex": regex_pattern, "$options": "i"}}
                ]
            }

            # Get total count for pagination
            total_count = await collection.count_documents(search_query)

            # Calculate skip value for pagination
            skip = (page - 1) * limit

            # Perform regex search
            cursor = collection.find(
                search_query,
                {
                    "title": 1,
                    "url": 1,
                    "Host": 1,
                    "publication_date": 1,
                    "Cleaned Data": 1,
                    "content": 1,
                    "readability_score": 1
                }
            ).skip(skip).limit(limit)

            articles = await cursor.to_list(length=limit)

            # Format articles for response
            for article in articles:
                # Generate preview text
                content = article.get('Cleaned Data', '') or article.get('content', '')
                preview = _generate_preview(content)

                formatted_articles.append({
                    "url": article["url"],
                    "title": article.get("title", "Untitled"),
                    "host": article.get("Host", ""),
                    "publication_date": article.get("publication_date"),
                    "preview": preview,
                    "readability_score": article.get("readability_score"),
                    "relevance_score": 0  # No relevance score for regex search
                })

        # Calculate pagination info
        total_pages = (total_count + limit - 1) // limit  # Ceiling division

        return {
            "query": q,
            "articles": formatted_articles,
            "total": total_count,
            "page": page,
            "limit": limit,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching articles: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


def _generate_preview(content: str, max_length: int = 200) -> str:
    """
    Generate a preview text from article content.

    Args:
        content: Article content
        max_length: Maximum length of preview

    Returns:
        Preview text
    """
    if not content:
        return "No preview available"

    # Clean and truncate content
    preview = content.strip()

    # Remove excessive whitespace
    preview = re.sub(r'\s+', ' ', preview)

    if len(preview) > max_length:
        preview = preview[:max_length].rsplit(' ', 1)[0] + "..."

    return preview

"""
ML Service - Dedicated microservice for machine learning operations.

This service handles all ML-related operations including:
- Vector embeddings generation
- Similarity search
- Topic analysis
- Text processing for ML

Communication: HTTP API called by Celery workers
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

from services.vector_service import VectorSimilarityService
from services.topic_service import TopicService
from database.connection import connect_to_database, close_database_connection
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global services
vector_service = None
topic_service = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup."""
    global vector_service, topic_service

    try:
        logger.info("🚀 Initializing ML Service...")

        # Connect to database first
        await connect_to_database()
        logger.info("✓ Database connected")

        # Initialize vector service
        vector_service = VectorSimilarityService()
        await vector_service.initialize()
        logger.info("✓ Vector service initialized")

        # Initialize topic service
        topic_service = TopicService()
        await topic_service.initialize()
        logger.info("✓ Topic service initialized")

        logger.info("✅ ML Service ready!")

        yield

    except Exception as e:
        logger.error(f"❌ Failed to initialize ML service: {e}")
        raise
    finally:
        logger.info("🔄 ML Service shutting down...")
        await close_database_connection()


# Create FastAPI app
app = FastAPI(
    title="ML Service",
    description="Dedicated microservice for ML operations",
    version="1.0.0",
    lifespan=lifespan
)


# Pydantic models for API
class EmbeddingRequest(BaseModel):
    text: str
    article_id: Optional[str] = None


class EmbeddingResponse(BaseModel):
    embedding: List[float]
    model_name: str
    success: bool


class SimilarityRequest(BaseModel):
    article: Dict[str, Any]
    limit: int = 10
    similarity_threshold: float = 0.7
    exclude_self: bool = True


class SimilarityResponse(BaseModel):
    similar_articles: List[Dict[str, Any]]
    success: bool


class TopicAnalysisRequest(BaseModel):
    article_url: str


class TopicAnalysisResponse(BaseModel):
    topics: List[str]
    topic_groups: List[Dict[str, Any]]
    success: bool


# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ml-service",
        "vector_service_ready": vector_service is not None,
        "topic_service_ready": topic_service is not None
    }


@app.get("/gpu-info")
async def gpu_info():
    """Get GPU information and status."""
    import torch

    gpu_info = {
        "cuda_available": torch.cuda.is_available(),
        "cuda_device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "current_device": torch.cuda.current_device() if torch.cuda.is_available() else None,
        "device_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "vector_service_device": vector_service.device if vector_service else None
    }

    if torch.cuda.is_available():
        gpu_info.update({
            "gpu_memory_allocated": torch.cuda.memory_allocated(0),
            "gpu_memory_reserved": torch.cuda.memory_reserved(0),
            "gpu_memory_total": torch.cuda.get_device_properties(0).total_memory
        })

    return gpu_info


# Vector operations endpoints
@app.post("/embeddings/generate", response_model=EmbeddingResponse)
async def generate_embedding(request: EmbeddingRequest):
    """Generate embedding for text."""
    try:
        if not vector_service:
            raise HTTPException(status_code=503, detail="Vector service not initialized")

        # Prepare article-like structure for embedding
        article = {
            "title": "",
            "content": request.text,
            "url": request.article_id or "unknown"
        }

        embedding = await vector_service.generate_embedding(article)

        if embedding is None:
            raise HTTPException(status_code=500, detail="Failed to generate embedding")

        return EmbeddingResponse(
            embedding=embedding,
            model_name=vector_service.model_name,
            success=True
        )

    except Exception as e:
        logger.error(f"Error generating embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/embeddings/batch", response_model=Dict[str, Any])
async def batch_generate_embeddings(batch_size: int = 100):
    """Generate embeddings for multiple articles."""
    try:
        if not vector_service:
            raise HTTPException(status_code=503, detail="Vector service not initialized")

        result = await vector_service.batch_generate_embeddings(batch_size)
        return result

    except Exception as e:
        logger.error(f"Error in batch embedding generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/similarity/search", response_model=SimilarityResponse)
async def find_similar_articles(request: SimilarityRequest):
    """Find articles similar to the given article."""
    try:
        if not vector_service:
            raise HTTPException(status_code=503, detail="Vector service not initialized")

        similar_articles = await vector_service.find_similar_articles(
            article=request.article,
            limit=request.limit,
            similarity_threshold=request.similarity_threshold,
            exclude_self=request.exclude_self
        )

        return SimilarityResponse(
            similar_articles=similar_articles,
            success=True
        )

    except Exception as e:
        logger.error(f"Error finding similar articles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Summary embedding endpoints
class SummaryEmbeddingRequest(BaseModel):
    summary_text: str
    article_url: Optional[str] = None


class SummarySimilarityRequest(BaseModel):
    article_url: str
    limit: int = 10
    similarity_threshold: float = 0.7


@app.post("/embeddings/summary/generate", response_model=EmbeddingResponse)
async def generate_summary_embedding(request: SummaryEmbeddingRequest):
    """Generate embedding for summary text."""
    try:
        if not vector_service:
            raise HTTPException(status_code=503, detail="Vector service not initialized")

        embedding = await vector_service.generate_summary_embedding(request.summary_text)

        if embedding is None:
            raise HTTPException(status_code=500, detail="Failed to generate summary embedding")

        return EmbeddingResponse(
            embedding=embedding,
            model_name=vector_service.model_name,
            success=True
        )

    except Exception as e:
        logger.error(f"Error generating summary embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/similarity/search-by-summary", response_model=SimilarityResponse)
async def find_similar_articles_by_summary(request: SummarySimilarityRequest):
    """Find articles similar to the given article based on summary embeddings."""
    try:
        if not vector_service:
            raise HTTPException(status_code=503, detail="Vector service not initialized")

        similar_articles = await vector_service.find_similar_articles_by_summary(
            article_url=request.article_url,
            limit=request.limit,
            similarity_threshold=request.similarity_threshold
        )

        return SimilarityResponse(
            similar_articles=similar_articles,
            success=True
        )

    except Exception as e:
        logger.error(f"Error finding similar articles by summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Topic analysis endpoints
@app.post("/topics/analyze", response_model=TopicAnalysisResponse)
async def analyze_topics(request: TopicAnalysisRequest):
    """Analyze topics for an article."""
    try:
        if not topic_service:
            raise HTTPException(status_code=503, detail="Topic service not initialized")

        result = await topic_service.analyze_article_topics(request.article_url)

        return TopicAnalysisResponse(
            topics=result.get("topics", []),
            topic_groups=result.get("topic_groups", []),
            success=result.get("success", False)
        )

    except Exception as e:
        logger.error(f"Error analyzing topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/topics/group", response_model=Dict[str, Any])
async def group_articles_by_topics(
    similarity_threshold: float = 0.75,
    min_group_size: int = 2
):
    """Group articles by topics."""
    try:
        if not topic_service:
            raise HTTPException(status_code=503, detail="Topic service not initialized")

        result = await topic_service.group_articles_by_topics(
            similarity_threshold=similarity_threshold,
            min_group_size=min_group_size
        )

        return result

    except Exception as e:
        logger.error(f"Error grouping articles by topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class SimilarArticlesDisplayRequest(BaseModel):
    article_url: str
    limit: int = 5


class SimilarArticlesDisplayResponse(BaseModel):
    similar_articles: List[Dict[str, Any]]
    success: bool


@app.post("/topics/similar-for-display", response_model=SimilarArticlesDisplayResponse)
async def get_similar_articles_for_display(request: SimilarArticlesDisplayRequest):
    """Get similar articles formatted for frontend display."""
    try:
        if not topic_service:
            raise HTTPException(status_code=503, detail="Topic service not initialized")

        similar_articles = await topic_service.get_similar_articles_for_display(
            request.article_url,
            limit=request.limit
        )

        return SimilarArticlesDisplayResponse(
            similar_articles=similar_articles,
            success=True
        )

    except Exception as e:
        logger.error(f"Error getting similar articles for display: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ArticleTopicsRequest(BaseModel):
    article_url: str


class ArticleTopicsResponse(BaseModel):
    topic_groups: List[Dict[str, Any]]
    success: bool


class DailyTopicsRequest(BaseModel):
    days_back: int = 7
    similarity_threshold: float = 0.80  # High threshold for quality topics
    min_group_size: int = 5  # At least 5 articles per topic
    max_articles: int = 500  # Limit articles for performance


class DailyTopicsResponse(BaseModel):
    success: bool
    topic_groups: List[Dict[str, Any]]
    articles_processed: int
    articles_grouped: int


@app.post("/topics/generate-daily-topics", response_model=DailyTopicsResponse)
async def generate_daily_topics(request: DailyTopicsRequest):
    """
    Generate topic groups from recent articles with date filtering.

    This endpoint handles all similarity calculations and grouping logic.
    """
    try:
        from datetime import datetime, timedelta
        from database.connection import db_manager
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity

        logger.info(f"Generating daily topics for last {request.days_back} days")

        db = db_manager.get_database()
        collection = db["documents"]

        # Query for articles from last N days with summaries and embeddings
        cutoff_date = datetime.now() - timedelta(days=request.days_back)

        query = {
            "publication_date": {
                "$gte": cutoff_date,
                "$type": "date"
            },
            "summary": {"$exists": True, "$ne": None, "$ne": ""},
            "summary_processing_status": "completed",
            "embedding": {"$exists": True}
        }

        cursor = collection.find(query, {
            "url": 1,
            "title": 1,
            "summary": 1,
            "publication_date": 1,
            "origin": 1,
            "Host": 1,
            "embedding": 1,
            "image_url": 1,
            "author": 1,
            "_id": 1
        }).sort("publication_date", -1)  # Most recent first

        articles = await cursor.to_list(length=request.max_articles)
        logger.info(f"Found {len(articles)} articles for grouping (limited to {request.max_articles})")

        if len(articles) < 2:
            return DailyTopicsResponse(
                success=True,
                topic_groups=[],
                articles_processed=len(articles),
                articles_grouped=0
            )

        # Group articles by similarity
        topic_groups = []
        processed_urls = set()

        for idx, seed_article in enumerate(articles):
            if seed_article['url'] in processed_urls:
                continue

            # Log progress
            if idx % 100 == 0:
                logger.info(f"Processed {idx}/{len(articles)} articles, found {len(topic_groups)} groups")

            seed_embedding = seed_article.get('embedding')
            if not seed_embedding:
                continue

            # Find similar articles
            similar_articles = [seed_article]
            seed_embedding_array = np.array(seed_embedding).reshape(1, -1)

            for article in articles:
                if article['url'] == seed_article['url']:
                    continue
                if article['url'] in processed_urls:
                    continue

                article_embedding = article.get('embedding')
                if not article_embedding:
                    continue

                # Check dimension match
                if len(article_embedding) != len(seed_embedding):
                    continue

                # Calculate cosine similarity
                article_embedding_array = np.array(article_embedding).reshape(1, -1)
                similarity = cosine_similarity(seed_embedding_array, article_embedding_array)[0][0]

                if similarity >= request.similarity_threshold:
                    similar_articles.append(article)

            # Create group if minimum size met
            if len(similar_articles) >= request.min_group_size:
                topic_group = {
                    "articles": [
                        {
                            "url": art.get('url'),
                            "title": art.get('title', 'Untitled'),
                            "summary": art.get('summary', ''),
                            "publication_date": art.get('publication_date').isoformat() if art.get('publication_date') else None,
                            "origin": art.get('origin', ''),
                            "host": art.get('Host', ''),
                            "image_url": art.get('image_url'),
                            "author": art.get('author')
                        }
                        for art in similar_articles
                    ],
                    "article_count": len(similar_articles)
                }

                topic_groups.append(topic_group)

                # Mark as processed
                for art in similar_articles:
                    processed_urls.add(art['url'])

                logger.info(f"Created topic group with {len(similar_articles)} articles")

        logger.info(f"Daily topics generation complete: {len(topic_groups)} groups, {len(processed_urls)} articles grouped")

        return DailyTopicsResponse(
            success=True,
            topic_groups=topic_groups,
            articles_processed=len(articles),
            articles_grouped=len(processed_urls)
        )

    except Exception as e:
        logger.error(f"Error generating daily topics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/topics/article-topics", response_model=ArticleTopicsResponse)
async def get_article_topics(request: ArticleTopicsRequest):
    """Get topic groups that contain the specified article."""
    try:
        if not topic_service:
            raise HTTPException(status_code=503, detail="Topic service not initialized")

        topic_groups = await topic_service.get_article_topics(request.article_url)

        return ArticleTopicsResponse(
            topic_groups=topic_groups,
            success=True
        )

    except Exception as e:
        logger.error(f"Error getting article topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)


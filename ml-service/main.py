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


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8081)


"""
Main FastAPI application setup.
"""

import logging
import json
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from database.connection import connect_to_database, close_database_connection
from database.articles import article_repository
from database.sources import source_repository
from scheduler.scheduler import start_scheduler, stop_scheduler
from scheduler.topic_scheduler import start_topic_scheduler, stop_topic_scheduler
from config import settings

logger = logging.getLogger(__name__)


async def initialize_topic_analysis():
    """Initialize the topic analysis system on startup."""
    try:
        logger.info("🔍 Initializing topic analysis system...")

        # Import here to avoid circular imports
        from services.vector_service import vector_service

        # Initialize vector service
        await vector_service.initialize()
        logger.info("✓ Vector service initialized")

        # Check if we need to generate embeddings for existing articles
        from database.connection import db_manager
        db = db_manager.get_database()
        collection = db["documents"]

        total_articles = await collection.count_documents({})
        articles_with_embeddings = await collection.count_documents({"embedding": {"$exists": True}})

        logger.info(f"📊 Found {total_articles} total articles, {articles_with_embeddings} with embeddings")

        # If we have articles without embeddings, queue batch generation
        if total_articles > 0 and articles_with_embeddings < total_articles:
            logger.info("🚀 Queueing batch embedding generation for existing articles...")
            try:
                # Import task locally to avoid circular imports
                from celery_app.tasks import batch_generate_embeddings

                # Queue the task asynchronously
                batch_generate_embeddings.delay(batch_size=50)
                logger.info("✓ Batch embedding generation queued")
            except Exception as e:
                logger.warning(f"⚠️ Failed to queue batch embedding generation: {e}")

        logger.info("✅ Topic analysis system initialized successfully")

    except Exception as e:
        logger.error(f"❌ Failed to initialize topic analysis system: {e}")
        # Don't raise - let the app continue without topic analysis
        logger.warning("⚠️ Continuing without topic analysis functionality")


class DateTimeEncoder(json.JSONEncoder):
    """Custom JSON encoder that properly serializes datetime objects with timezone info."""
    def default(self, obj):
        if isinstance(obj, datetime):
            # Ensure datetime is in UTC and format with timezone info
            if obj.tzinfo is None:
                # Assume naive datetime is UTC
                obj = obj.replace(tzinfo=datetime.timezone.utc)
            return obj.isoformat()
        return super().default(obj)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown tasks."""
    # Startup
    logger.info(f"🚀 {settings.app_name} starting up...")
    logger.info(f"📦 Version: {settings.build_version}")
    logger.info(f"🔗 Build: {settings.build_timestamp}")

    try:
        # Connect to database
        await connect_to_database()

        # Create database indexes
        await article_repository.create_indexes()
        await source_repository.create_indexes()

        # Initialize topic analysis system
        await initialize_topic_analysis()

        # Start schedulers
        start_scheduler()
        start_topic_scheduler()

        logger.info("✅ Application startup completed successfully")

    except Exception as e:
        logger.error(f"❌ Application startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("🔄 Shutting down application...")
    try:
        # Stop schedulers first
        stop_scheduler()
        stop_topic_scheduler()

        # Close database connection
        await close_database_connection()

        logger.info("✅ Application shutdown completed")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Modern Python-based news readability analysis system",
        lifespan=lifespan,
        debug=settings.debug,
        json_encoder=DateTimeEncoder  # Use custom datetime encoder
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:30005",
            "http://localhost:4912",
            "http://localhost:4913",
            "https://news.sparksplex.com",
            "http://news.sparksplex.com",
            "*"
        ],  # Allow both localhost and external domain
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    register_routes(app)

    # Exception handlers
    register_exception_handlers(app)

    return app


def register_routes(app: FastAPI):
    """Register all application routes."""

    # Import route modules
    from .routes import sources, daily, graph, export, scan, summaries, topic_routes, topic_management_routes

    # Include route modules with /api prefix
    app.include_router(sources.router, prefix="/api/sources", tags=["sources"])
    app.include_router(daily.router, prefix="/api/daily", tags=["daily"])
    app.include_router(graph.router, prefix="/api/graph", tags=["graph"])
    app.include_router(export.router, prefix="/api/export", tags=["export"])
    app.include_router(scan.router, prefix="/api/scan", tags=["scan"])
    app.include_router(summaries.router, prefix="/api/summaries", tags=["summaries"])
    app.include_router(topic_routes.router, tags=["topics"])
    app.include_router(topic_management_routes.router, tags=["topic-management"])

    # Web page routes (without /api prefix)
    @app.get("/", include_in_schema=False)
    async def root():
        """Redirect root to sources page."""
        return RedirectResponse(url="/sources", status_code=302)

    @app.get("/sources", include_in_schema=False)
    async def sources_page(request: Request):
        """Serve the sources management page."""
        from fastapi.templating import Jinja2Templates
        from database.sources import source_repository
        from config import settings

        templates = Jinja2Templates(directory="templates")
        sources_with_stats = await source_repository.get_sources_with_stats()

        return templates.TemplateResponse("pages/sources.html", {
            "request": request,
            "sources": sources_with_stats,
            "title": "News Sources Management",
            "buildTimestamp": settings.build_timestamp,
            "buildVersion": settings.build_version
        })

    @app.get("/daily", include_in_schema=False)
    async def daily_page(request: Request):
        """Serve the daily report page."""
        from fastapi.templating import Jinja2Templates
        from database.articles import article_repository
        from config import settings
        from datetime import datetime, timedelta

        templates = Jinja2Templates(directory="templates")

        # Get query parameters
        start_param = request.query_params.get("start")
        end_param = request.query_params.get("end")

        # Parse date parameters
        if end_param:
            end_date = datetime.strptime(end_param, "%Y-%m-%d")
        else:
            end_date = datetime.now()

        if start_param:
            start_date = datetime.strptime(start_param, "%Y-%m-%d")
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

        return templates.TemplateResponse("pages/daily.html", {
            "request": request,
            "results": results,
            "dates": dates,
            "title": "Daily News Readability Report",
            "buildTimestamp": settings.build_timestamp,
            "buildVersion": settings.build_version
        })

    @app.get("/graph", include_in_schema=False)
    async def graph_page(request: Request):
        """Serve the graph visualization page."""
        from fastapi.templating import Jinja2Templates

        templates = Jinja2Templates(directory="templates")
        return templates.TemplateResponse("pages/graph.html", {"request": request})

    # Summary management page
    @app.get("/summaries-page", include_in_schema=False)
    async def summaries_page(request: Request):
        """Serve the summary management page."""
        from fastapi.templating import Jinja2Templates

        templates = Jinja2Templates(directory="templates")
        return templates.TemplateResponse("pages/summaries.html", {"request": request})

    # Newspaper page
    @app.get("/newspaper", include_in_schema=False)
    async def newspaper_page(request: Request):
        """Serve the newspaper-style today's news page."""
        from fastapi.templating import Jinja2Templates

        templates = Jinja2Templates(directory="templates")
        return templates.TemplateResponse("pages/newspaper.html", {"request": request})

    # Article viewer page
    @app.get("/article-viewer", include_in_schema=False)
    async def article_viewer_page(request: Request):
        """Serve the article viewer page for finding similar articles."""
        from fastapi.templating import Jinja2Templates

        templates = Jinja2Templates(directory="templates")
        return templates.TemplateResponse("pages/article_viewer.html", {
            "request": request,
            "title": "Article Viewer"
        })

    # Topic management page
    @app.get("/topic-management", include_in_schema=False)
    async def topic_management_page(request: Request):
        """Serve the topic analysis management page."""
        from fastapi.templating import Jinja2Templates

        templates = Jinja2Templates(directory="templates")
        return templates.TemplateResponse("pages/topic_management.html", {
            "request": request,
            "title": "Topic Analysis Management"
        })


    # Health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check():
        """Health check endpoint with Celery queue status."""
        from database.connection import db_manager
        from scheduler.scheduler import rss_scheduler
        from scheduler.topic_scheduler import topic_scheduler
        from celery_app.queue_manager import queue_manager

        db_healthy = await db_manager.health_check()
        scheduler_status = rss_scheduler.get_status()
        topic_scheduler_status = topic_scheduler.get_status()
        queue_stats = await queue_manager.get_queue_stats()

        celery_healthy = queue_stats.get("success", False)
        overall_healthy = db_healthy and scheduler_status["running"] and celery_healthy

        health_status = {
            "status": "healthy" if overall_healthy else "unhealthy",
            "version": settings.app_version,
            "build_version": settings.build_version,
            "build_timestamp": settings.build_timestamp,
            "database": "connected" if db_healthy else "disconnected",
            "scheduler": scheduler_status,
            "topic_scheduler": topic_scheduler_status,
            "celery": {
                "status": "connected" if celery_healthy else "disconnected",
                "active_tasks": queue_stats.get("total_active_tasks", 0),
                "queues": queue_stats.get("queues", {})
            }
        }

        status_code = 200 if overall_healthy else 503
        return health_status


def register_exception_handlers(app: FastAPI):
    """Register global exception handlers."""

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler for unhandled errors."""
        logger.error(f"Unhandled exception in {request.url}: {exc}", exc_info=True)

        return {
            "error": "Internal server error",
            "detail": str(exc) if settings.debug else "An unexpected error occurred",
            "path": str(request.url)
        }


# Create the application instance
app = create_app()

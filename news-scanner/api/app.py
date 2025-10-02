"""
Main FastAPI application setup.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from database.connection import connect_to_database, close_database_connection
from database.articles import article_repository
from database.sources import source_repository
from scheduler.scheduler import start_scheduler, stop_scheduler
from config import settings

# OpenTelemetry instrumentation
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

logger = logging.getLogger(__name__)


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

        # Start RSS scheduler
        start_scheduler()

        logger.info("✅ Application startup completed successfully")

    except Exception as e:
        logger.error(f"❌ Application startup failed: {e}")
        raise

    yield

    # Shutdown
    logger.info("🔄 Shutting down application...")
    try:
        # Stop scheduler first
        stop_scheduler()

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
        debug=settings.debug
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:4912", "http://localhost:4913", "*"],  # Allow both services
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    register_routes(app)

    # Exception handlers
    register_exception_handlers(app)

    # Instrument FastAPI with OpenTelemetry
    FastAPIInstrumentor.instrument_app(app)

    return app


def register_routes(app: FastAPI):
    """Register all application routes."""

    # Import route modules
    from .routes import sources, daily, graph, export, scan, summaries

    # Include route modules
    app.include_router(sources.router, prefix="/sources", tags=["sources"])
    app.include_router(daily.router, prefix="/daily", tags=["daily"])
    app.include_router(graph.router, prefix="/graph", tags=["graph"])
    app.include_router(export.router, prefix="/export", tags=["export"])
    app.include_router(scan.router, prefix="/scan", tags=["scan"])
    app.include_router(summaries.router, prefix="/summaries", tags=["summaries"])

    # Root redirect
    @app.get("/", include_in_schema=False)
    async def root():
        """Redirect root to sources page."""
        return RedirectResponse(url="/sources", status_code=302)

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


    # Health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check():
        """Health check endpoint with Celery queue status."""
        from database.connection import db_manager
        from scheduler.scheduler import rss_scheduler
        from celery_app.queue_manager import queue_manager

        db_healthy = await db_manager.health_check()
        scheduler_status = rss_scheduler.get_status()
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

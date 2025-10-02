"""
Main entry point for the News Scanner service.
"""

import logging
import sys
import os
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# OpenTelemetry instrumentation setup
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.pymongo import PymongoInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

# Initialize OpenTelemetry
def setup_telemetry():
    """Setup OpenTelemetry instrumentation for the news scanner service."""
    # Create resource
    resource = Resource.create({
        "service.name": os.getenv("OTEL_SERVICE_NAME", "news-scanner"),
        "service.version": "1.0.0",
        "deployment.environment": os.getenv("ENVIRONMENT", "development")
    })

    # Set up tracer provider
    trace.set_tracer_provider(TracerProvider(resource=resource))
    tracer = trace.get_tracer_provider().get_tracer(__name__)

    # Set up OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"),
        insecure=True
    )

    # Add span processor
    span_processor = BatchSpanProcessor(otlp_exporter)
    trace.get_tracer_provider().add_span_processor(span_processor)

    # Instrument libraries
    RequestsInstrumentor().instrument()
    PymongoInstrumentor().instrument()
    RedisInstrumentor().instrument()
    CeleryInstrumentor().instrument()

    return tracer

# Setup telemetry
tracer = setup_telemetry()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('news-scanner.log')
    ]
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    import uvicorn
    from config import settings

    logger.info(f"🚀 Starting {settings.app_name}")
    logger.info(f"📡 Server: {settings.host}:{settings.port}")
    logger.info(f"🔗 Environment: {'DEBUG' if settings.debug else 'PRODUCTION'}")

    # Run the FastAPI application
    uvicorn.run(
        "api.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    )

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

# Set up OpenTelemetry logging before configuring logging
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.logging import LoggingInstrumentor

# Set up OpenTelemetry
trace.set_tracer_provider(TracerProvider())
tracer = trace.get_tracer(__name__)

# Configure OTLP exporter for traces
otlp_exporter = OTLPSpanExporter(
    endpoint="http://host.docker.internal:30007",
    insecure=True
)

# Add span processor
span_processor = BatchSpanProcessor(otlp_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)

# Set up OpenTelemetry logging
LoggingInstrumentor().instrument()

# Configure logging with OpenTelemetry
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

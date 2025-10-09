# ML Service - GPU-enabled with optimized caching
FROM python:3.11-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip first
RUN pip install --upgrade pip

# Create pip cache directory
RUN mkdir -p /root/.cache/pip

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install dependencies with cache mount
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --use-deprecated=legacy-resolver -r requirements.txt

# Install automatic instrumentation
RUN opentelemetry-bootstrap --action=install

# Production stage
FROM base as production

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8081

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8081/health')" || exit 1

# Run the ML service
CMD ["opentelemetry-instrument", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8081"]


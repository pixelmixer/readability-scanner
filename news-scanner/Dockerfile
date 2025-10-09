# Optimized Dockerfile with minimal ML dependencies
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --use-deprecated=legacy-resolver -r requirements.txt

# Install automatic instrumentation
RUN opentelemetry-bootstrap --action=install

# Create directories for logs and data
RUN mkdir -p /app/logs

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Run the application with automatic instrumentation
CMD ["opentelemetry-instrument", "python", "main.py"]

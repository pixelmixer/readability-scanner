#!/bin/bash

# SigNoz Startup Script for News Analysis System
# This script starts the SigNoz observability platform and the news analysis services

echo "🚀 Starting SigNoz Observability Platform for News Analysis System"
echo "=================================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating SigNoz directories..."
mkdir -p signoz/data/clickhouse
mkdir -p signoz/logs

# Start ClickHouse first
echo "🔧 Starting ClickHouse..."
docker-compose up -d signoz-clickhouse

# Wait for ClickHouse to be ready
echo "⏳ Waiting for ClickHouse to initialize..."
sleep 15

# Initialize SigNoz database and tables
echo "🗄️  Initializing SigNoz database schema..."
docker exec crawltest-signoz-clickhouse-1 clickhouse-client --query "CREATE DATABASE IF NOT EXISTS signoz_metrics" || echo "Database may already exist"
docker exec crawltest-signoz-clickhouse-1 clickhouse-client --query "CREATE TABLE IF NOT EXISTS signoz_metrics.distributed_updated_metadata (metric_name String, type String, description String, temporality String, is_monotonic UInt8, unit String, updated_at DateTime DEFAULT now()) ENGINE = MergeTree() ORDER BY metric_name" || echo "Table may already exist"

# Start remaining SigNoz services
echo "🔧 Starting remaining SigNoz services..."
docker-compose up -d signoz-otel-collector signoz-query-service signoz-frontend

# Wait for SigNoz to be ready
echo "⏳ Waiting for SigNoz services to initialize (this may take a few minutes)..."
sleep 30

# Check if SigNoz is ready
echo "🔍 Checking SigNoz status..."
if curl -s http://localhost:3301 > /dev/null; then
    echo "✅ SigNoz frontend is ready!"
else
    echo "⚠️  SigNoz frontend is not ready yet, but continuing..."
fi

# Start the news analysis services
echo "📰 Starting news analysis services..."
docker-compose up -d

echo ""
echo "🎉 Setup Complete!"
echo "=================="
echo ""
echo "📊 SigNoz Dashboard: http://localhost:3301"
echo "🔍 Query Service: http://localhost:8080"
echo "📈 News Scanner: http://localhost:4913"
echo "🤗 Hug API: http://localhost:3839"
echo "🌉 RSS Bridge: http://localhost:3939"
echo "🌸 Celery Flower: http://localhost:5555"
echo ""
echo "📋 To view logs:"
echo "   docker-compose logs -f [service-name]"
echo ""
echo "🛑 To stop all services:"
echo "   docker-compose down"
echo ""
echo "📚 For more information, check the SigNoz documentation:"
echo "   https://signoz.io/docs/"

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

# Start SigNoz services first
echo "🔧 Starting SigNoz services..."
docker-compose up -d signoz-clickhouse signoz-otel-collector signoz-query-service signoz-frontend signoz-alertmanager

# Wait for SigNoz to be ready
echo "⏳ Waiting for SigNoz to initialize (this may take a few minutes)..."
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

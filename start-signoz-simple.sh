#!/bin/bash

# Simple SigNoz Startup Script
# This script starts SigNoz with automatic database initialization

echo "Starting SigNoz with automatic database initialization..."

# Start ClickHouse first
echo "Starting ClickHouse..."
docker-compose up -d signoz-clickhouse

# Wait for ClickHouse to be ready
echo "Waiting for ClickHouse to initialize..."
sleep 15

# Run database initialization
echo "Initializing database..."
docker-compose up signoz-db-init

# Start remaining services
echo "Starting remaining services..."
docker-compose up -d

echo ""
echo "SigNoz is ready!"
echo "Dashboard: http://localhost:3301"
echo "Query Service: http://localhost:8080"

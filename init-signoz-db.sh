#!/bin/bash

# SigNoz Database Initialization Script
# This script initializes the required ClickHouse database and tables for SigNoz

echo "🗄️  Initializing SigNoz Database Schema"
echo "====================================="

# Check if ClickHouse is running
echo "🔍 Checking if ClickHouse is running..."
if ! docker exec crawltest-signoz-clickhouse-1 clickhouse-client --query "SELECT 1" > /dev/null 2>&1; then
    echo "❌ ClickHouse is not running. Please start it first with:"
    echo "   docker-compose up -d signoz-clickhouse"
    exit 1
fi
echo "✅ ClickHouse is running"

# Create database
echo "📊 Creating signoz_metrics database..."
if docker exec crawltest-signoz-clickhouse-1 clickhouse-client --query "CREATE DATABASE IF NOT EXISTS signoz_metrics"; then
    echo "✅ Database created/verified"
else
    echo "❌ Failed to create database"
    exit 1
fi

# Create table
echo "📋 Creating distributed_updated_metadata table..."
if docker exec crawltest-signoz-clickhouse-1 clickhouse-client --query "CREATE TABLE IF NOT EXISTS signoz_metrics.distributed_updated_metadata (metric_name String, type String, description String, temporality String, is_monotonic UInt8, unit String, updated_at DateTime DEFAULT now()) ENGINE = MergeTree() ORDER BY metric_name"; then
    echo "✅ Table created/verified"
else
    echo "❌ Failed to create table"
    exit 1
fi

# Verify the setup
echo "🔍 Verifying database setup..."
if docker exec crawltest-signoz-clickhouse-1 clickhouse-client --query "SHOW TABLES FROM signoz_metrics" | grep -q "distributed_updated_metadata"; then
    echo "✅ Database setup verified successfully!"
else
    echo "⚠️  Table not found in verification"
fi

echo ""
echo "🎉 Database initialization complete!"
echo "You can now start the SigNoz Query Service:"
echo "   docker-compose up -d signoz-query-service"

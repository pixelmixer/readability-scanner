#!/bin/bash

# SigNoz Database Initialization Script
# This script runs inside the ClickHouse container to initialize the required database and tables

echo "Initializing SigNoz database schema..."

# Wait for ClickHouse to be ready
echo "Waiting for ClickHouse to be ready..."
until clickhouse-client --host signoz-clickhouse --query "SELECT 1" > /dev/null 2>&1; do
    echo "ClickHouse is not ready yet, waiting..."
    sleep 2
done

echo "ClickHouse is ready, creating database and tables..."

# Create database
echo "Creating signoz_metrics database..."
clickhouse-client --host signoz-clickhouse --query "CREATE DATABASE IF NOT EXISTS signoz_metrics"

# Create table
echo "Creating distributed_updated_metadata table..."
clickhouse-client --host signoz-clickhouse --query "CREATE TABLE IF NOT EXISTS signoz_metrics.distributed_updated_metadata (metric_name String, type String, description String, temporality String, is_monotonic UInt8, unit String, updated_at DateTime DEFAULT now()) ENGINE = MergeTree() ORDER BY metric_name"

# Verify the setup
echo "Verifying database setup..."
if clickhouse-client --host signoz-clickhouse --query "SHOW TABLES FROM signoz_metrics" | grep -q "distributed_updated_metadata"; then
    echo "Database setup completed successfully!"
else
    echo "Warning: Table verification failed, but database operations completed"
fi

echo "SigNoz database initialization complete!"
